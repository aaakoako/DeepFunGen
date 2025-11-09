"""重新生成WowGirls视频的funscript，使用最新的优化算法"""
import json
from pathlib import Path
import pandas as pd
import numpy as np

import sys
from pathlib import Path

# 添加DeepFunGen.py到路径
sys.path.insert(0, str(Path(__file__).parent / "DeepFunGen.py"))

from backend.parameter_recommender import recommend_parameters
from backend.postprocess import run_postprocess, write_funscript
from backend.models import PostprocessOptionsModel

def main():
    BASE_DIR = Path(r'G:\Download\DZMM\WowGirls 19-12-24 Beautiful Slave Game XXX-Scene1')
    VIDEO_NAME = "WowGirls 19-12-24 Beautiful Slave Game XXX-Scene1"
    
    csv_path = BASE_DIR / f"{VIDEO_NAME}.conv_tcn_62.csv"
    if not csv_path.exists():
        print(f"错误: 未找到CSV文件 {csv_path}")
        return
    
    print("=" * 80)
    print("重新生成WowGirls视频的funscript（使用最新优化算法）")
    print("=" * 80)
    print(f"视频: {VIDEO_NAME}")
    print()
    
    # 读取CSV
    print("读取CSV文件...")
    df = pd.read_csv(csv_path)
    
    # 确保有必要的列
    if 'predicted_change' not in df.columns:
        print("错误: CSV文件中没有 'predicted_change' 列")
        return
    
    # 计算帧率（从timestamp_ms推断）
    if 'timestamp_ms' in df.columns:
        duration_ms = df['timestamp_ms'].iloc[-1] - df['timestamp_ms'].iloc[0]
        frame_count = len(df)
        frame_rate = (frame_count / duration_ms) * 1000.0 if duration_ms > 0 else 30.0
    else:
        frame_rate = 30.0  # 默认30fps
    
    print(f"  帧数: {len(df)}")
    print(f"  帧率: {frame_rate:.2f} fps")
    print()
    
    # 获取推荐参数
    print("分析信号特征并获取推荐参数...")
    print("使用基于信号强度分布的拟真体验优化算法")
    recommended, features, reasoning = recommend_parameters(df)
    
    print("推荐参数:")
    print(f"  smooth_window_frames: {recommended.smooth_window_frames}")
    print(f"  prominence_ratio: {recommended.prominence_ratio:.3f}")
    if 'intensity_adjustment' in features:
        print(f"    强度调整因子: {features['intensity_adjustment']:.2f}")
    if 'high_intensity_ratio' in features:
        print(f"    高强度区域: {features['high_intensity_ratio']:.1%}, 低强度区域: {features['low_intensity_ratio']:.1%}")
    print(f"  min_prominence: {recommended.min_prominence:.3f}")
    print(f"  max_slope: {recommended.max_slope:.1f}")
    print(f"  boost_slope: {recommended.boost_slope:.1f}")
    print(f"  min_slope: {recommended.min_slope:.1f}")
    print(f"  merge_threshold_ms: {recommended.merge_threshold_ms:.1f}")
    print(f"  fft_denoise: {recommended.fft_denoise}")
    print(f"  fft_frames_per_component: {recommended.fft_frames_per_component}")
    print()
    
    # 生成funscript
    print("生成funscript...")
    processed = run_postprocess(df, recommended, frame_rate)
    
    # 保存funscript
    output_path = BASE_DIR / f"{VIDEO_NAME}.funscript"
    model_name = "conv_tcn_62"
    
    write_funscript(processed, output_path, model_name, recommended)
    
    print(f"已保存: {output_path}")
    print()
    
    # 分析生成的funscript
    print("分析生成的funscript...")
    with open(output_path, 'r', encoding='utf-8') as f:
        generated_data = json.load(f)
    
    generated_actions = generated_data.get('actions', [])
    if generated_actions:
        timestamps = [a['at'] for a in generated_actions]
        positions = [a['pos'] for a in generated_actions]
        
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        position_changes = [abs(positions[i+1] - positions[i]) for i in range(len(positions)-1)]
        
        duration_ms = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        
        print(f"  总动作数: {len(generated_actions)}")
        print(f"  时长: {duration_ms/1000:.1f}秒")
        print(f"  平均间隔: {sum(intervals)/len(intervals) if intervals else 0:.1f}ms")
        print(f"  动作频率: {len(generated_actions) / (duration_ms / 1000.0) if duration_ms > 0 else 0:.2f} actions/s")
        print(f"  平均位置变化: {sum(position_changes)/len(position_changes) if position_changes else 0:.2f}")
        print(f"  极端位置比例: {sum(1 for p in positions if p <= 10 or p >= 90) / len(positions) if positions else 0:.1%}")
        print(f"  中心位置比例: {sum(1 for p in positions if 40 <= p <= 60) / len(positions) if positions else 0:.1%}")
        print(f"  快速变化比例: {sum(1 for change in position_changes if change > 50) / len(position_changes) if position_changes else 0:.1%}")
        print(f"  缓慢变化比例: {sum(1 for change in position_changes if change < 5) / len(position_changes) if position_changes else 0:.1%}")
    
    print()
    print("=" * 80)
    print("生成完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

