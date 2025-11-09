"""Parameter recommendation module based on signal features."""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from .models import PostprocessOptionsModel
from .signal_analyzer import analyze_prediction_signal


def recommend_parameters(df: pd.DataFrame) -> Tuple[PostprocessOptionsModel, Dict[str, float], str]:
    """
    Recommend post-processing parameters based on signal features.
    
    Args:
        df: DataFrame with 'predicted_change' column
        
    Returns:
        Tuple of (recommended_options, features_dict, reasoning_text)
    """
    # Extract features
    features = analyze_prediction_signal(df)
    
    # Analyze signal intensity distribution for realistic experience
    intensity_features = analyze_signal_intensity_distribution(df)
    features.update(intensity_features)
    
    # Get recommendations from different aspects
    freq_rec = recommend_by_frequency(features)
    amp_rec = recommend_by_amplitude(features)
    smooth_rec = recommend_by_smoothness(features)
    
    # Calculate base prominence_ratio before intensity adjustment
    base_prominence_ratio = max(freq_rec["prominence_ratio"], smooth_rec["prominence_ratio"])
    features["base_prominence_ratio"] = base_prominence_ratio
    
    # Get intensity-based recommendations (for realistic experience)
    intensity_rec = recommend_by_intensity_distribution(features)
    
    # Combine recommendations (frequency has highest priority)
    recommended = PostprocessOptionsModel()
    
    # Apply frequency-based recommendations (highest priority)
    recommended.min_slope = freq_rec["min_slope"]
    recommended.merge_threshold_ms = freq_rec["merge_threshold_ms"]
    recommended.prominence_ratio = freq_rec["prominence_ratio"]
    
    # Apply amplitude-based recommendations
    recommended.max_slope = amp_rec["max_slope"]
    recommended.boost_slope = amp_rec["boost_slope"]  # Add boost_slope recommendation
    recommended.smooth_window_frames = amp_rec["smooth_window_frames"]
    
    # Apply smoothness-based recommendations
    recommended.min_prominence = smooth_rec["min_prominence"]
    
    # Apply intensity-based adjustments for realistic experience
    # Adjust prominence_ratio based on intensity distribution
    # High intensity regions (climax) -> lower prominence (allow more actions)
    # Low intensity regions (calm) -> higher prominence (reduce actions)
    recommended.prominence_ratio = intensity_rec.get("prominence_ratio", base_prominence_ratio)
    
    # Store intensity-based recommendations for reasoning
    features["intensity_adjustment"] = intensity_rec.get("adjustment_factor", 1.0)
    
    # FFT settings based on signal characteristics
    if features["main_frequency"] > 0.01:  # Has periodic component
        recommended.fft_denoise = True
        # Adjust FFT frames based on period length
        if features["period_length"] > 0:
            recommended.fft_frames_per_component = max(5, min(20, int(features["period_length"] / 2)))
        else:
            recommended.fft_frames_per_component = 10
    else:
        # Low frequency or no clear periodicity
        recommended.fft_denoise = True  # Still use FFT for noise reduction
        recommended.fft_frames_per_component = 10
    
    # Generate reasoning text
    reasoning = _generate_reasoning(features, freq_rec, amp_rec, smooth_rec)
    
    return recommended, features, reasoning


def recommend_by_frequency(features: Dict[str, float]) -> Dict[str, float]:
    """
    Recommend parameters based on frequency characteristics.
    
    Higher frequency -> lower min_slope, higher merge_threshold_ms
    Lower frequency -> higher min_slope, lower merge_threshold_ms
    """
    main_freq = features.get("main_frequency", 0.0)
    period_length = features.get("period_length", 0.0)
    
    # Normalize frequency (assuming typical range 0-0.1 for video signals)
    freq_normalized = min(1.0, main_freq * 100)  # Scale to 0-1
    
    # min_slope: inversely related to frequency (continuous mapping)
    # High frequency -> more rapid changes -> lower min_slope needed
    # Low frequency -> slower changes -> higher min_slope to avoid too many actions
    # Based on 8-video test: actions_per_second still +11.4% vs manual
    # Need more aggressive filtering: 1.5-3.0 (was 2.0-4.5)
    # Continuous mapping: 1.5 (high freq) to 3.0 (low freq) - more aggressive
    min_slope = max(1.5, min(3.0, 1.5 + 1.5 * (1.0 - freq_normalized)))
    
    # merge_threshold_ms: directly related to frequency (continuous mapping)
    # High frequency -> shorter periods -> lower merge threshold
    # Low frequency -> longer periods -> higher merge threshold
    # Core goal: Frequency similarity - match manual script action frequency
    # Analysis shows: manual scripts have 97.1% intervals <200ms, avg 131.4ms
    # Tool-generated: only 8.8% intervals <200ms, avg 354.8ms (65.3% in 200-400ms range)
    # 400ms threshold is too high, causing precision loss and delay
    # Need precision-focused range: 150-300ms to preserve more detail and improve accuracy
    # This is the KEY parameter to match frequency AND improve precision
    # Continuous mapping: 150ms (high freq, high precision) to 300ms (low freq, lower precision)
    if period_length > 0:
        # Convert period length (in frames) to milliseconds (assuming 30fps)
        period_ms = (period_length / 30.0) * 1000.0
        # Use period-based calculation with precision-focused range: 150-300ms
        merge_threshold_ms = max(150.0, min(300.0, period_ms * 0.15))  # Precision-focused multiplier
    else:
        # Continuous mapping based on frequency: 150ms (high freq) to 300ms (low freq)
        merge_threshold_ms = 150.0 + (300.0 - 150.0) * (1.0 - freq_normalized)
    
    # prominence_ratio: adjust based on extrema density (continuous mapping)
    # This is KEY to reduce action density and filter small fluctuations
    # Higher prominence_ratio = fewer extrema points = fewer actions
    # Core goal: Frequency similarity - reduce action frequency to match manual scripts
    # Based on pure motion video test: 0.35 caused -75.6% frequency difference (too aggressive)
    # Pure motion video target: 7.61 actions/s, generated: 1.86 actions/s
    # Need aggressive reduction: 0.10-0.20 to match pure motion video frequency
    # Continuous mapping: 0.10 (low density) to 0.20 (high density) - aggressive filtering reduction
    extrema_density = features.get("extrema_density", 0.0)
    prominence_ratio = 0.10 + min(0.10, extrema_density * 1.0)  # Aggressive base and multiplier
    
    return {
        "min_slope": min_slope,
        "merge_threshold_ms": merge_threshold_ms,
        "prominence_ratio": prominence_ratio,
    }


def recommend_by_amplitude(features: Dict[str, float]) -> Dict[str, float]:
    """
    Recommend parameters based on amplitude characteristics.
    
    Large amplitude changes -> higher max_slope, larger smooth window
    Small amplitude changes -> lower max_slope, smaller smooth window
    """
    mean_change = features.get("mean_change", 0.0)
    max_change = features.get("max_change", 0.0)
    range_val = features.get("range", 0.0)
    
    # Normalize amplitude (assuming typical range 0-1 for predicted_change)
    # Use range as primary indicator, with mean_change as secondary
    avg_amplitude = (mean_change + max_change) / 2.0
    # Better normalization: use actual range of the signal
    range_normalized = min(1.0, range_val) if range_val > 0 else 0.0
    amplitude_normalized = min(1.0, (avg_amplitude * 2.0 + range_normalized) / 2.0)
    
    # max_slope: directly related to amplitude (continuous mapping)
    # Keep in reasonable range 2.5-4.0 to prevent extreme jumps
    # Don't over-reduce as it limits rate of change, not absolute change
    # The rapid_changes_ratio issue should be solved by merge_threshold_ms and prominence_ratio
    # Continuous mapping: 2.5 (small) to 4.0 (large) - reasonable range
    max_slope = 2.5 + 1.5 * amplitude_normalized
    
    # boost_slope: similar to max_slope but slightly lower
    # Keep in reasonable range 1.5-3.0
    # Continuous mapping: 1.5 (small) to 3.0 (large) - reasonable range
    boost_slope = 1.5 + 1.5 * amplitude_normalized
    
    # smooth_window_frames: inversely related to amplitude variability (continuous mapping)
    # High variability -> smaller window to preserve details
    # Low variability -> larger window for smoother output
    # Based on 8-video test: slow_changes_ratio still 1% vs manual 8% (+191%)
    # Need much more smoothing: 5-8 (was 3-6)
    # Continuous mapping: 5 (high variability) to 8 (low variability) - much more aggressive
    std_change = features.get("std_change", 0.0)
    if std_change > 0.15:
        smooth_window_frames = 5
    elif std_change > 0.08:
        smooth_window_frames = 6
    elif std_change > 0.03:
        smooth_window_frames = 7
    else:
        smooth_window_frames = 8
    
    return {
        "max_slope": max_slope,
        "boost_slope": boost_slope,
        "smooth_window_frames": smooth_window_frames,
    }


def recommend_by_smoothness(features: Dict[str, float]) -> Dict[str, float]:
    """
    Recommend parameters based on signal smoothness.
    
    Rough signal -> higher prominence_ratio, higher min_prominence
    Smooth signal -> lower prominence_ratio, lower min_prominence
    """
    smoothness = features.get("smoothness", 1.0)
    stability = features.get("stability", 1.0)
    
    # Combined smoothness metric
    combined_smoothness = (smoothness + stability) / 2.0
    
    # prominence_ratio: inversely related to smoothness (continuous mapping)
    # Rough signal -> need higher threshold to filter noise
    # Smooth signal -> can use lower threshold
    # IMPORTANT: This should align with recommend_by_frequency range (0.10-0.20)
    # to ensure prominence_ratio is high enough to filter small fluctuations
    # Continuous mapping: 0.10 (smooth) to 0.20 (rough) - aligned with frequency-based recommendation
    prominence_ratio = 0.10 + 0.10 * (1.0 - combined_smoothness)
    
    # min_prominence: also inversely related to smoothness (continuous mapping)
    # Continuous mapping: 0.0 (smooth) to 0.015 (rough)
    min_prominence = 0.015 * (1.0 - combined_smoothness)
    
    return {
        "prominence_ratio": prominence_ratio,
        "min_prominence": min_prominence,
    }


def _generate_reasoning(
    features: Dict[str, float],
    freq_rec: Dict[str, float],
    amp_rec: Dict[str, float],
    smooth_rec: Dict[str, float],
) -> str:
    """Generate human-readable reasoning for the recommendations."""
    parts = []
    
    # Frequency analysis
    main_freq = features.get("main_frequency", 0.0)
    if main_freq > 0.01:
        parts.append(f"Signal shows periodic behavior (frequency: {main_freq:.4f})")
    else:
        parts.append("Signal shows low or no clear periodicity")
    
    # Amplitude analysis
    mean_change = features.get("mean_change", 0.0)
    if mean_change > 0.1:
        parts.append("Large amplitude changes detected")
    elif mean_change > 0.05:
        parts.append("Moderate amplitude changes")
    else:
        parts.append("Small amplitude changes")
    
    # Smoothness analysis
    smoothness = features.get("smoothness", 1.0)
    if smoothness < 0.5:
        parts.append("Signal is relatively rough, using higher prominence thresholds")
    elif smoothness > 0.7:
        parts.append("Signal is smooth, using lower prominence thresholds")
    
    # Intensity distribution analysis (for realistic experience)
    high_intensity_ratio = features.get("high_intensity_ratio", 0.5)
    low_intensity_ratio = features.get("low_intensity_ratio", 0.5)
    intensity_adjustment = features.get("intensity_adjustment", 1.0)
    
    if high_intensity_ratio > 0.3:
        parts.append(f"High-intensity regions detected ({high_intensity_ratio:.1%}), allowing more actions for climax scenes")
    if low_intensity_ratio > 0.3:
        parts.append(f"Low-intensity regions detected ({low_intensity_ratio:.1%}), reducing actions for calm scenes")
    
    if abs(intensity_adjustment - 1.0) > 0.05:
        if intensity_adjustment < 1.0:
            parts.append(f"Adjusted prominence for more dynamic experience (factor: {intensity_adjustment:.2f})")
        else:
            parts.append(f"Adjusted prominence for smoother experience (factor: {intensity_adjustment:.2f})")
    
    # Extrema density
    extrema_density = features.get("extrema_density", 0.0)
    if extrema_density > 0.1:
        parts.append("High density of extrema points, filtering with prominence")
    elif extrema_density < 0.02:
        parts.append("Low density of extrema points")
    
    if not parts:
        return "Standard parameters recommended based on signal analysis"
    
    return ". ".join(parts) + "."


def analyze_signal_intensity_distribution(df: pd.DataFrame) -> Dict[str, float]:
    """
    Analyze signal intensity distribution to identify high-intensity (climax) and 
    low-intensity (calm) regions for realistic experience.
    
    Args:
        df: DataFrame with 'predicted_change' column
        
    Returns:
        Dictionary of intensity distribution features
    """
    if "predicted_change" not in df.columns:
        return {}
    
    signal = df["predicted_change"].values.astype(float)
    n = len(signal)
    
    if n < 10:
        return {
            "high_intensity_ratio": 0.5,
            "low_intensity_ratio": 0.5,
            "intensity_variance": 0.0,
        }
    
    # Calculate signal intensity (absolute value of predicted_change)
    intensity = np.abs(signal)
    
    # Calculate statistics
    mean_intensity = np.mean(intensity)
    std_intensity = np.std(intensity)
    median_intensity = np.median(intensity)
    
    # Define thresholds for high/low intensity regions
    # High intensity: > mean + 0.5*std (climax regions)
    # Low intensity: < mean - 0.5*std (calm regions)
    high_threshold = mean_intensity + 0.5 * std_intensity
    low_threshold = max(0.0, mean_intensity - 0.5 * std_intensity)
    
    # Calculate ratios
    high_intensity_count = np.sum(intensity > high_threshold)
    low_intensity_count = np.sum(intensity < low_threshold)
    high_intensity_ratio = high_intensity_count / n if n > 0 else 0.0
    low_intensity_ratio = low_intensity_count / n if n > 0 else 0.0
    
    # Calculate intensity variance (how much intensity varies across the signal)
    # Higher variance means more variation between climax and calm regions
    intensity_variance = std_intensity / (mean_intensity + 1e-9)  # Coefficient of variation
    
    return {
        "high_intensity_ratio": float(high_intensity_ratio),
        "low_intensity_ratio": float(low_intensity_ratio),
        "intensity_variance": float(intensity_variance),
        "mean_intensity": float(mean_intensity),
        "median_intensity": float(median_intensity),
    }


def recommend_by_intensity_distribution(features: Dict[str, float]) -> Dict[str, float]:
    """
    Recommend parameters based on signal intensity distribution for realistic experience.
    
    Strategy:
    - High intensity regions (climax) -> lower prominence_ratio (allow more actions, extreme positions)
    - Low intensity regions (calm) -> higher prominence_ratio (reduce actions, center positions)
    - Balance between the two based on their ratios
    
    Args:
        features: Dictionary of signal features including intensity distribution
        
    Returns:
        Dictionary of recommended parameters
    """
    high_intensity_ratio = features.get("high_intensity_ratio", 0.5)
    low_intensity_ratio = features.get("low_intensity_ratio", 0.5)
    intensity_variance = features.get("intensity_variance", 0.0)
    base_prominence = features.get("base_prominence_ratio", 0.25)
    
    # Adjustment factor based on intensity distribution
    # If there are more high-intensity regions, we want to allow more actions (lower prominence)
    # If there are more low-intensity regions, we want to reduce actions (higher prominence)
    # Balance: if high_intensity_ratio > low_intensity_ratio, reduce prominence slightly
    #          if low_intensity_ratio > high_intensity_ratio, increase prominence slightly
    
    intensity_balance = high_intensity_ratio - low_intensity_ratio  # Range: -1 to 1
    
    # Adjustment: 
    # - If more high-intensity regions (climax), reduce prominence by up to 20%
    # - If more low-intensity regions (calm), increase prominence by up to 20%
    # - Higher variance means more variation, so adjust more
    adjustment_factor = 1.0 - (intensity_balance * 0.15 * (1.0 + min(intensity_variance, 1.0)))
    adjustment_factor = max(0.8, min(1.2, adjustment_factor))  # Clamp to 0.8-1.2
    
    adjusted_prominence = base_prominence * adjustment_factor
    
    # Ensure prominence_ratio stays in reasonable range (0.10-0.20)
    adjusted_prominence = max(0.10, min(0.20, adjusted_prominence))
    
    return {
        "prominence_ratio": adjusted_prominence,
        "adjustment_factor": adjustment_factor,
    }


__all__ = [
    "recommend_parameters", 
    "recommend_by_frequency", 
    "recommend_by_amplitude", 
    "recommend_by_smoothness",
    "analyze_signal_intensity_distribution",
    "recommend_by_intensity_distribution",
]

