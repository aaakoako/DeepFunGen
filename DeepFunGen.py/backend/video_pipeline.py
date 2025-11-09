"""Video decoding and ONNX inference pipeline."""
from __future__ import annotations

import csv
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np
import pandas as pd

from .onnx_runner import OnnxSequenceModel


@dataclass
class PipelineResult:
    frame_count: int
    fps: float
    timestamps: np.ndarray
    predicted_change: np.ndarray
    predictions_df: pd.DataFrame
    prediction_path: Path
    model_name: str


class ProcessingCancelled(Exception):
    """Raised when a job cancellation is detected mid-processing."""


def resolve_prediction_path(video_path: Path, model_path: Path) -> Path:
    video_dir = video_path.parent
    csv_name = f"{video_path.stem}.{model_path.stem}.csv"
    return video_dir / csv_name


def resolve_script_path(video_path: Path) -> Path:
    return video_path.parent / f"{video_path.stem}.funscript"


def process_video(
    video_path: Path,
    model: OnnxSequenceModel,
    *,
    progress_cb: Callable[[float, str], None],
    should_cancel: Callable[[], bool],
    log_cb: Callable[[str], None],
) -> PipelineResult:
    """Run the core video -> predictions pipeline."""

    if should_cancel():
        raise ProcessingCancelled()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 1e-3:
        fps = 30.0

    total_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_est <= 0:
        total_est = 0

    per_frame_shape = (model.HEIGHT, model.WIDTH, model.CHANNELS)
    window = deque(maxlen=model.SEQUENCE_LENGTH)
    predicted_changes: list[float] = []

    frame_index = 0
    frame_ms = 1000.0 / fps
    log_cb(f"Decoding video at ~{fps:.2f} fps")

    try:
        while True:
            if should_cancel():
                raise ProcessingCancelled()

            ret, frame = cap.read()
            if not ret or frame is None:
                break
            if frame.size == 0:
                continue

            resized = cv2.resize(frame, (model.WIDTH, model.HEIGHT), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            normalized = rgb.astype(np.float32) / 255.0

            if normalized.shape != per_frame_shape:
                normalized = normalized.reshape(per_frame_shape)

            window.append(normalized)

            if len(predicted_changes) <= frame_index:
                predicted_changes.extend([0.0] * (frame_index - len(predicted_changes) + 1))

            if len(window) == model.SEQUENCE_LENGTH:
                sequence = np.stack(window, axis=0)
                value = model.infer(sequence)
                predicted_changes[frame_index] = value
            else:
                predicted_changes[frame_index] = 0.0

            frame_index += 1

            if total_est > 0:
                progress = min(1.0, frame_index / total_est)
                if frame_index % max(1, total_est // 20 or 1) == 0:
                    progress_cb(progress, f"Processing {frame_index}/{total_est} frames")
            else:
                if frame_index % 30 == 0:
                    progress_cb(float("nan"), f"Processing {frame_index} frames")

        progress_cb(0.95, "Finalising predictions")
    finally:
        cap.release()

    frame_count = frame_index
    if frame_count == 0:
        raise RuntimeError("No frames decoded from video")

    predicted = np.array(predicted_changes[:frame_count], dtype=np.float32)
    if predicted.size < frame_count:
        extra = frame_count - predicted.size
        predicted = np.pad(predicted, (0, extra), constant_values=0.0)

    cutoff = min(model.SEQUENCE_LENGTH - 1, predicted.size)
    if cutoff > 0:
        predicted[:cutoff] = 0.0

    timestamps = np.arange(frame_count, dtype=np.float64) * frame_ms

    df = pd.DataFrame(
        {
            "frame_index": np.arange(frame_count, dtype=np.int32),
            "timestamp_ms": timestamps,
            "predicted_change": predicted,
        }
    )

    model_name = model.model_path.stem
    prediction_path = resolve_prediction_path(video_path, model.model_path)
    prediction_path.parent.mkdir(parents=True, exist_ok=True)
    with prediction_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame_index", "timestamp_ms", "predicted_change"])
        for frame_idx in range(frame_count):
            writer.writerow([
                frame_idx,
                f"{timestamps[frame_idx]:.6f}",
                f"{predicted[frame_idx]:.9f}",
            ])

    return PipelineResult(
        frame_count=frame_count,
        fps=fps,
        timestamps=timestamps,
        predicted_change=predicted,
        predictions_df=df,
        prediction_path=prediction_path,
        model_name=model_name,
    )


def quick_predict_for_recommendation(
    video_path: Path,
    model: OnnxSequenceModel,
    *,
    frames_per_segment: int = 250,
) -> pd.DataFrame:
    """
    Perform quick prediction on selected video segments for parameter recommendation.
    
    This function intelligently samples video segments based on total frame count
    to get representative signal data without processing the entire video.
    
    Args:
        video_path: Path to video file
        model: OnnxSequenceModel instance
        frames_per_segment: Number of frames to sample per segment (default 250)
        
    Returns:
        DataFrame with frame_index, timestamp_ms, and predicted_change columns
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video: {video_path}")
    
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 1e-3:
        fps = 30.0
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        # If frame count is unknown, process a small sample
        total_frames = 1000
        cap.release()
        raise RuntimeError("Cannot determine video frame count")
    
    # Calculate number of segments based on total frames
    if total_frames < 5000:  # < 3 minutes @ 30fps
        num_segments = 2
    elif total_frames < 20000:  # 3-11 minutes
        num_segments = 4
    elif total_frames < 60000:  # 11-33 minutes
        num_segments = 6
    else:  # > 33 minutes
        num_segments = 10
    
    # Adjust frames_per_segment for very short videos
    if total_frames < frames_per_segment * num_segments:
        frames_per_segment = max(100, total_frames // (num_segments + 1))
    
    # Select representative segments
    segments = _select_representative_segments(total_frames, num_segments, frames_per_segment)
    
    per_frame_shape = (model.HEIGHT, model.WIDTH, model.CHANNELS)
    window = deque(maxlen=model.SEQUENCE_LENGTH)
    all_predictions = []
    frame_ms = 1000.0 / fps
    
    try:
        for seg_start, seg_end in segments:
            # Seek to segment start
            cap.set(cv2.CAP_PROP_POS_FRAMES, seg_start)
            
            segment_predictions = []
            local_frame_idx = 0
            
            while local_frame_idx < (seg_end - seg_start):
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                if frame.size == 0:
                    continue
                
                global_frame_idx = seg_start + local_frame_idx
                
                resized = cv2.resize(frame, (model.WIDTH, model.HEIGHT), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                normalized = rgb.astype(np.float32) / 255.0
                
                if normalized.shape != per_frame_shape:
                    normalized = normalized.reshape(per_frame_shape)
                
                window.append(normalized)
                
                predicted_value = 0.0
                if len(window) == model.SEQUENCE_LENGTH:
                    sequence = np.stack(window, axis=0)
                    predicted_value = model.infer(sequence)
                
                timestamp_ms = global_frame_idx * frame_ms
                segment_predictions.append({
                    "frame_index": global_frame_idx,
                    "timestamp_ms": timestamp_ms,
                    "predicted_change": predicted_value,
                })
                
                local_frame_idx += 1
            
            all_predictions.extend(segment_predictions)
    finally:
        cap.release()
    
    if not all_predictions:
        raise RuntimeError("No frames processed from video segments")
    
    # Create DataFrame from all predictions
    df = pd.DataFrame(all_predictions)
    df = df.sort_values("frame_index").reset_index(drop=True)
    
    return df


def _select_representative_segments(
    total_frames: int,
    num_segments: int,
    frames_per_segment: int,
) -> list[tuple[int, int]]:
    """
    Select representative video segments for sampling.
    
    Args:
        total_frames: Total number of frames in video
        num_segments: Number of segments to sample
        frames_per_segment: Frames to sample per segment
        
    Returns:
        List of (start_frame, end_frame) tuples
    """
    segments = []
    
    if num_segments == 1:
        # Single segment from middle
        start = max(0, (total_frames - frames_per_segment) // 2)
        end = min(total_frames, start + frames_per_segment)
        segments.append((start, end))
    elif num_segments == 2:
        # Beginning and end
        segments.append((0, min(frames_per_segment, total_frames)))
        segments.append((max(0, total_frames - frames_per_segment), total_frames))
    else:
        # Distribute segments across video
        # Always include beginning and end
        segments.append((0, min(frames_per_segment, total_frames)))
        
        # Distribute middle segments
        if num_segments > 2:
            step = total_frames / (num_segments - 1)
            for i in range(1, num_segments - 1):
                center = int(i * step)
                start = max(0, center - frames_per_segment // 2)
                end = min(total_frames, start + frames_per_segment)
                if end > start:
                    segments.append((start, end))
        
        # End segment
        if num_segments > 1:
            segments.append((max(0, total_frames - frames_per_segment), total_frames))
    
    # Remove overlapping segments and ensure they're sorted
    segments = sorted(set(segments), key=lambda x: x[0])
    
    return segments


__all__ = [
    "PipelineResult",
    "ProcessingCancelled",
    "process_video",
    "quick_predict_for_recommendation",
    "resolve_prediction_path",
    "resolve_script_path",
]
