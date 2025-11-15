"""Signal analysis module for extracting features from prediction signals."""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
from scipy import stats
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks


def analyze_prediction_signal(df: pd.DataFrame) -> Dict[str, float]:
    """
    Extract comprehensive features from a prediction signal DataFrame.
    
    Args:
        df: DataFrame with 'predicted_change' column
        
    Returns:
        Dictionary of extracted features
    """
    if "predicted_change" not in df.columns:
        raise ValueError("DataFrame must contain 'predicted_change' column")
    
    signal = df["predicted_change"].values.astype(float)
    n = len(signal)
    
    if n < 3:
        # Return default values for very short signals
        return _default_features()
    
    features = {}
    
    # 1. Basic statistics
    features["mean"] = float(np.mean(signal))
    features["std"] = float(np.std(signal))
    features["range"] = float(np.ptp(signal))  # peak-to-peak
    features["median"] = float(np.median(signal))
    
    # 2. Change magnitude
    if n > 1:
        changes = np.diff(signal)
        features["mean_change"] = float(np.mean(np.abs(changes)))
        features["max_change"] = float(np.max(np.abs(changes)))
        features["std_change"] = float(np.std(changes))
    else:
        features["mean_change"] = 0.0
        features["max_change"] = 0.0
        features["std_change"] = 0.0
    
    # 3. Frequency features (FFT analysis)
    main_freq, period_length = _extract_frequency_features(signal)
    features["main_frequency"] = main_freq
    features["period_length"] = period_length
    
    # 4. Extrema density
    features["extrema_density"] = _calculate_extrema_density(signal)
    
    # 5. Signal smoothness (second derivative)
    features["smoothness"] = _calculate_smoothness(signal)
    
    # 6. Distribution features
    features["skewness"] = float(stats.skew(signal))
    features["kurtosis"] = float(stats.kurtosis(signal))
    
    # 7. Periodicity (autocorrelation)
    periodicity, period = _calculate_periodicity(signal)
    features["periodicity"] = periodicity
    if period > 0:
        features["period"] = float(period)
    else:
        features["period"] = features.get("period_length", 0.0)
    
    # 8. Stability (sliding window variance)
    features["stability"] = _calculate_stability(signal)
    
    return features


def _default_features() -> Dict[str, float]:
    """Return default feature values for edge cases."""
    return {
        "mean": 0.0,
        "std": 0.0,
        "range": 0.0,
        "median": 0.0,
        "mean_change": 0.0,
        "max_change": 0.0,
        "std_change": 0.0,
        "main_frequency": 0.0,
        "period_length": 0.0,
        "extrema_density": 0.0,
        "smoothness": 1.0,
        "skewness": 0.0,
        "kurtosis": 0.0,
        "periodicity": 0.0,
        "period": 0.0,
        "stability": 1.0,
    }


def _extract_frequency_features(signal: np.ndarray) -> tuple[float, float]:
    """Extract main frequency and period length using FFT."""
    n = len(signal)
    if n < 4:
        return 0.0, 0.0
    
    # Apply windowing to reduce spectral leakage
    windowed = signal * np.hanning(n)
    
    # Compute FFT
    fft_vals = fft(windowed)
    freqs = fftfreq(n)
    
    # Get power spectrum (only positive frequencies)
    power = np.abs(fft_vals[:n//2]) ** 2
    freqs_pos = freqs[:n//2]
    
    # Find dominant frequency (excluding DC component)
    if len(power) > 1:
        # Skip DC component (index 0)
        dominant_idx = np.argmax(power[1:]) + 1
        main_freq = abs(freqs_pos[dominant_idx])
        
        # Convert to period length in samples
        if main_freq > 0:
            period_length = float(1.0 / main_freq) if main_freq > 0 else 0.0
        else:
            period_length = 0.0
    else:
        main_freq = 0.0
        period_length = 0.0
    
    return float(main_freq), float(period_length)


def _calculate_extrema_density(signal: np.ndarray) -> float:
    """Calculate density of extrema points (peaks and troughs)."""
    n = len(signal)
    if n < 3:
        return 0.0
    
    # Find peaks and troughs with minimal prominence
    threshold = max(np.ptp(signal) * 0.05, 0.01)
    
    peaks, _ = find_peaks(signal, prominence=threshold)
    troughs, _ = find_peaks(-signal, prominence=threshold)
    
    total_extrema = len(peaks) + len(troughs)
    density = total_extrema / n if n > 0 else 0.0
    
    return float(density)


def _calculate_smoothness(signal: np.ndarray) -> float:
    """Calculate signal smoothness using second derivative."""
    n = len(signal)
    if n < 3:
        return 1.0
    
    # Second derivative (rate of change of first derivative)
    first_diff = np.diff(signal)
    second_diff = np.diff(first_diff)
    
    # Smoothness is inverse of second derivative magnitude
    # Higher values = smoother signal
    if len(second_diff) == 0:
        return 1.0
    
    avg_second_diff = np.mean(np.abs(second_diff))
    signal_range = np.ptp(signal)
    
    if signal_range > 0:
        smoothness = 1.0 / (1.0 + avg_second_diff / signal_range)
    else:
        smoothness = 1.0
    
    return float(np.clip(smoothness, 0.0, 1.0))


def _calculate_periodicity(signal: np.ndarray) -> tuple[float, float]:
    """Calculate periodicity using autocorrelation."""
    n = len(signal)
    if n < 4:
        return 0.0, 0.0
    
    # Normalize signal
    signal_norm = signal - np.mean(signal)
    signal_std = np.std(signal_norm)
    
    if signal_std == 0:
        return 0.0, 0.0
    
    signal_norm = signal_norm / signal_std
    
    # Compute autocorrelation
    autocorr = np.correlate(signal_norm, signal_norm, mode='full')
    autocorr = autocorr[n-1:]  # Take only positive lags
    autocorr = autocorr / autocorr[0]  # Normalize
    
    # Find first significant peak after lag 0
    # Look for peaks in the first half of the signal
    search_range = min(n // 2, len(autocorr))
    if search_range < 3:
        return 0.0, 0.0
    
    # Find peaks with prominence > 0.1
    peaks, properties = find_peaks(autocorr[1:search_range], prominence=0.1)
    
    if len(peaks) > 0:
        # First significant peak
        period = float(peaks[0] + 1)  # +1 because we skipped lag 0
        periodicity = float(autocorr[int(period)])
    else:
        period = 0.0
        periodicity = 0.0
    
    return float(periodicity), float(period)


def _calculate_stability(signal: np.ndarray, window_size: int = 100) -> float:
    """Calculate signal stability using sliding window variance."""
    n = len(signal)
    if n < window_size:
        # For short signals, use overall variance
        variance = np.var(signal)
        signal_range = np.ptp(signal)
        if signal_range > 0:
            stability = 1.0 / (1.0 + variance / signal_range)
        else:
            stability = 1.0
        return float(np.clip(stability, 0.0, 1.0))
    
    # Calculate variance in sliding windows
    window_variances = []
    for i in range(0, n - window_size + 1, window_size // 2):
        window = signal[i:i + window_size]
        window_variances.append(np.var(window))
    
    if len(window_variances) == 0:
        return 1.0
    
    # Stability is inverse of variance of variances
    # Lower variance of variances = more stable signal
    variance_of_variances = np.var(window_variances)
    mean_variance = np.mean(window_variances)
    
    if mean_variance > 0:
        stability = 1.0 / (1.0 + variance_of_variances / mean_variance)
    else:
        stability = 1.0
    
    return float(np.clip(stability, 0.0, 1.0))


__all__ = ["analyze_prediction_signal"]

