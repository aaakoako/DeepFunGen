"""Post-processing helpers for predictions and funscript output."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .postprocessor import PostProcessConfig, apply_postprocessing
from .models import PostprocessOptionsModel

GENERATOR_NAME = "DeepFunGen"
GENERATOR_VERSION = "1.0.0"


def build_postprocess_config(options: PostprocessOptionsModel, frame_rate: float) -> PostProcessConfig:
    return PostProcessConfig(
        frame_rate=frame_rate,
        smooth_window_frames=options.smooth_window_frames,
        prominence_ratio=options.prominence_ratio,
        min_prominence=options.min_prominence,
        max_slope=options.max_slope,
        boost_slope=options.boost_slope,
        min_slope=options.min_slope,
        merge_threshold_ms=options.merge_threshold_ms,
        fft_denoise=options.fft_denoise,
        fft_frames_per_component=options.fft_frames_per_component,
        fft_window_frames=options.fft_window_frames,
    )


def run_postprocess(
    predictions: pd.DataFrame,
    options: PostprocessOptionsModel,
    frame_rate: float,
) -> pd.DataFrame:
    config = build_postprocess_config(options, frame_rate)
    processed = apply_postprocessing(predictions, config)
    processed.attrs.setdefault("options", options.dict())
    processed.attrs.setdefault("frame_rate", frame_rate)
    # Store original signal for intensity-based position adjustment
    if "predicted_change" in predictions.columns:
        processed.attrs["original_signal"] = predictions["predicted_change"].values
    return processed


def write_funscript(
    processed: pd.DataFrame,
    output_path: Path,
    model_name: str,
    options: PostprocessOptionsModel,
) -> None:
    frame_rate = processed.attrs.get("frame_rate", 30.0)
    actions = _build_actions(processed, frame_rate)
    payload = {
        "version": "1.0",
        "inverted": False,
        "range": 100,
        "actions": actions,
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "model": model_name,
            "options": options.dict(),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _build_actions(processed: pd.DataFrame, frame_rate: float) -> List[Dict[str, int]]:
    meta = processed.attrs.get("postprocess", {}) if hasattr(processed, "attrs") else {}
    graph_points = meta.get("graph_points", []) if isinstance(meta, dict) else []
    
    # Get original predicted_change signal for intensity-based position adjustment
    original_signal = None
    if "predicted_change" in processed.columns:
        original_signal = processed["predicted_change"].values
    elif hasattr(processed, "attrs") and "original_signal" in processed.attrs:
        original_signal = processed.attrs["original_signal"]
    
    # Calculate intensity thresholds if we have the signal
    intensity_thresholds = None
    if original_signal is not None and len(original_signal) > 10:
        intensity = np.abs(original_signal)
        mean_intensity = np.mean(intensity)
        std_intensity = np.std(intensity)
        high_threshold = mean_intensity + 0.5 * std_intensity
        low_threshold = max(0.0, mean_intensity - 0.5 * std_intensity)
        intensity_thresholds = {
            "high": float(high_threshold),
            "low": float(low_threshold),
            "mean": float(mean_intensity),
        }
    
    actions: List[Dict[str, int]] = []
    if graph_points:
        last_time = -1
        step_ms = 1000.0 / frame_rate if frame_rate > 1e-6 else 33.3
        for point in graph_points:
            position = float(point.get("position", 0.0))
            value = float(point.get("value", 50.0))
            time_ms = int(round(position * step_ms))
            if last_time >= 0 and time_ms <= last_time:
                time_ms = last_time + 1
            
            # Adjust position based on signal intensity for realistic experience
            adjusted_value = _adjust_position_by_intensity(
                value, 
                time_ms, 
                step_ms, 
                original_signal, 
                intensity_thresholds
            )
            
            amplitude = int(round(float(np.clip(adjusted_value, 0.0, 100.0))))
            actions.append({"at": max(0, time_ms), "pos": amplitude})
            last_time = time_ms
    if not actions:
        series = processed.get("processed_value") if isinstance(processed, pd.DataFrame) else None
        if series is not None:
            step_ms = 1000.0 / frame_rate if frame_rate > 1e-6 else 33.3
            
            # Get intensity thresholds for position adjustment
            intensity_thresholds = None
            if original_signal is not None and len(original_signal) > 10:
                intensity = np.abs(original_signal)
                mean_intensity = np.mean(intensity)
                std_intensity = np.std(intensity)
                high_threshold = mean_intensity + 0.5 * std_intensity
                low_threshold = max(0.0, mean_intensity - 0.5 * std_intensity)
                intensity_thresholds = {
                    "high": float(high_threshold),
                    "low": float(low_threshold),
                    "mean": float(mean_intensity),
                }
            
            for idx, value in enumerate(np.asarray(series, dtype=np.float64)):
                time_ms = int(round(idx * step_ms))
                
                # Adjust position based on signal intensity
                adjusted_value = _adjust_position_by_intensity(
                    value,
                    time_ms,
                    step_ms,
                    original_signal,
                    intensity_thresholds
                )
                
                amplitude = int(round(float(np.clip(adjusted_value, 0.0, 100.0))))
                actions.append({"at": max(0, time_ms), "pos": amplitude})
    if not actions:
        actions.append({"at": 0, "pos": 50})
    deduped: Dict[int, int] = {}
    for action in sorted(actions, key=lambda item: item["at"]):
        deduped[action["at"]] = action["pos"]
    
    # Apply smoothing to reduce rapid changes
    final_actions = _smooth_actions(deduped)
    return final_actions


def _smooth_actions(actions_dict: Dict[int, int], max_change_per_action: int = 15) -> List[Dict[str, int]]:
    """
    Smooth actions to reduce rapid changes by limiting position changes between consecutive actions.
    
    Core goal: Motion smoothness - ensure smooth transitions between actions.
    Based on pure motion video test: need to increase slow_changes_ratio from 7.1% to 34.0%
    
    Args:
        actions_dict: Dictionary mapping time_ms to position
        max_change_per_action: Maximum position change allowed between consecutive actions
                              Reduced from 20 to 15 for smoother motion and higher slow_changes_ratio
    
    Returns:
        List of smoothed actions
    """
    if not actions_dict:
        return []
    
    sorted_items = sorted(actions_dict.items())
    if len(sorted_items) < 2:
        return [{"at": sorted_items[0][0], "pos": sorted_items[0][1]}]
    
    smoothed: List[Dict[str, int]] = []
    last_time = -1
    last_pos = None
    
    for time_ms, pos in sorted_items:
        if last_time >= 0 and time_ms <= last_time:
            time_ms = last_time + 1
        
        # Apply smoothing: limit position change for smooth motion
        if last_pos is not None:
            change = pos - last_pos
            time_diff = time_ms - last_time
            
            # Calculate allowed change based on time difference
            # Longer time intervals allow larger changes, but still limited
            if time_diff > 0:
                # Allow up to max_change_per_action per 100ms
                max_allowed_change = max_change_per_action * (time_diff / 100.0)
                max_allowed_change = min(max_allowed_change, max_change_per_action * 2)  # Cap at 2x
            else:
                max_allowed_change = max_change_per_action
            
            if abs(change) > max_allowed_change:
                # Limit the change smoothly
                pos = last_pos + (max_allowed_change if change > 0 else -max_allowed_change)
                pos = max(0, min(100, pos))  # Clamp to valid range
        
        smoothed.append({"at": time_ms, "pos": int(round(pos))})
        last_time = time_ms
        last_pos = pos
    
    return smoothed


def _adjust_position_by_intensity(
    original_value: float,
    time_ms: int,
    step_ms: float,
    signal: Optional[np.ndarray],
    intensity_thresholds: Optional[Dict[str, float]],
) -> float:
    """
    Adjust position based on signal intensity for realistic experience.
    
    Strategy:
    - High intensity regions (climax) -> keep or enhance extreme positions (0-10, 90-100)
    - Low intensity regions (calm) -> adjust extreme positions to center range (30-50, 50-70)
    
    Args:
        original_value: Original position value (0-100)
        time_ms: Time in milliseconds
        step_ms: Milliseconds per frame
        signal: Original predicted_change signal array
        intensity_thresholds: Pre-calculated intensity thresholds
        
    Returns:
        Adjusted position value (0-100)
    """
    if signal is None or intensity_thresholds is None:
        return original_value
    
    # Calculate frame index from time
    frame_idx = int(round(time_ms / step_ms))
    if frame_idx < 0 or frame_idx >= len(signal):
        return original_value
    
    # Get signal intensity at this frame
    signal_value = signal[frame_idx]
    intensity = abs(signal_value)
    
    # Determine if this is a high or low intensity region
    is_high_intensity = intensity > intensity_thresholds["high"]
    is_low_intensity = intensity < intensity_thresholds["low"]
    
    # Check if original position is extreme (0-10 or 90-100)
    is_extreme_position = original_value <= 10.0 or original_value >= 90.0
    
    # Adjust position based on intensity
    if is_extreme_position:
        if is_low_intensity:
            # Low intensity region: adjust extreme positions to center range
            # Map 0-10 -> 35-55 (very centered), 90-100 -> 45-65 (very centered)
            if original_value <= 10.0:
                # Map 0-10 to 35-55 (very close to center 40-60)
                normalized = original_value / 10.0
                adjusted = 35.0 + normalized * 20.0  # 35-55
            else:  # original_value >= 90.0
                # Map 90-100 to 45-65 (very close to center 40-60)
                normalized = (original_value - 90.0) / 10.0
                adjusted = 45.0 + normalized * 20.0  # 45-65
            return adjusted
        elif is_high_intensity:
            # High intensity region: keep extreme positions (or slightly enhance)
            return original_value
        else:
            # Medium intensity: moderate adjustment towards center
            # Map 0-10 -> 30-50, 90-100 -> 50-70
            if original_value <= 10.0:
                normalized = original_value / 10.0
                adjusted = 30.0 + normalized * 20.0  # 30-50
            else:  # original_value >= 90.0
                normalized = (original_value - 90.0) / 10.0
                adjusted = 50.0 + normalized * 20.0  # 50-70
            return adjusted
    else:
        # Not extreme position, keep as is
        return original_value


__all__ = [
    "run_postprocess",
    "write_funscript",
    "build_postprocess_config",
]