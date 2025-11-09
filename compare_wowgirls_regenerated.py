"""对比重新生成的funscript与手工制作的纯运动funscript"""
import json
import statistics
from pathlib import Path
from typing import Dict

def analyze_funscript(funscript_path: Path) -> Dict:
    """分析 funscript 文件"""
    if not funscript_path.exists():
        return {}
    
    try:
        with open(funscript_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        actions = data.get('actions', [])
        if not actions:
            return {}
        
        timestamps = [a['at'] for a in actions]
        positions = [a['pos'] for a in actions]
        
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        position_changes = [abs(positions[i+1] - positions[i]) for i in range(len(positions)-1)]
        
        duration_ms = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
        
        return {
            'total_actions': len(actions),
            'duration_ms': duration_ms,
            'avg_interval_ms': statistics.mean(intervals) if intervals else 0,
            'actions_per_second': len(actions) / (duration_ms / 1000.0) if duration_ms > 0 else 0,
            'avg_position_change': statistics.mean(position_changes) if position_changes else 0,
            'extreme_positions_ratio': sum(1 for p in positions if p <= 10 or p >= 90) / len(positions) if positions else 0,
            'center_positions_ratio': sum(1 for p in positions if 40 <= p <= 60) / len(positions) if positions else 0,
            'rapid_changes_ratio': sum(1 for change in position_changes if change > 50) / len(position_changes) if position_changes else 0,
            'slow_changes_ratio': sum(1 for change in position_changes if change < 5) / len(position_changes) if position_changes else 0,
        }
    except Exception as e:
        print(f"  错误分析 {funscript_path.name}: {e}")
        return {}

def main():
    BASE_DIR = Path(r'G:\Download\DZMM\WowGirls 19-12-24 Beautiful Slave Game XXX-Scene1')
    VIDEO_NAME = "WowGirls 19-12-24 Beautiful Slave Game XXX-Scene1"
    
    print("=" * 80)
    print("对比重新生成的funscript与手工制作的纯运动funscript")
    print("=" * 80)
    print()
    
    # 分析重新生成的funscript
    generated_path = BASE_DIR / f"{VIDEO_NAME}.funscript"
    print("分析重新生成的funscript:")
    print("-" * 80)
    generated_stats = analyze_funscript(generated_path)
    if not generated_stats:
        print("错误: 未找到重新生成的funscript")
        return
    
    print(f"  总动作数: {generated_stats['total_actions']}")
    print(f"  时长: {generated_stats['duration_ms']/1000:.1f}秒")
    print(f"  平均间隔: {generated_stats['avg_interval_ms']:.1f}ms")
    print(f"  动作频率: {generated_stats['actions_per_second']:.2f} actions/s")
    print(f"  平均位置变化: {generated_stats['avg_position_change']:.2f}")
    print(f"  极端位置比例: {generated_stats['extreme_positions_ratio']:.1%}")
    print(f"  中心位置比例: {generated_stats['center_positions_ratio']:.1%}")
    print(f"  快速变化比例: {generated_stats['rapid_changes_ratio']:.1%}")
    print(f"  缓慢变化比例: {generated_stats['slow_changes_ratio']:.1%}")
    print()
    
    # 分析手工制作的funscript（pitch轴作为代表）
    manual_path = BASE_DIR / f"{VIDEO_NAME}.pitch.funscript"
    print("分析手工制作的funscript (pitch轴):")
    print("-" * 80)
    manual_stats = analyze_funscript(manual_path)
    if not manual_stats:
        print("错误: 未找到手工制作的funscript")
        return
    
    print(f"  总动作数: {manual_stats['total_actions']}")
    print(f"  时长: {manual_stats['duration_ms']/1000:.1f}秒")
    print(f"  平均间隔: {manual_stats['avg_interval_ms']:.1f}ms")
    print(f"  动作频率: {manual_stats['actions_per_second']:.2f} actions/s")
    print(f"  平均位置变化: {manual_stats['avg_position_change']:.2f}")
    print(f"  极端位置比例: {manual_stats['extreme_positions_ratio']:.1%}")
    print(f"  中心位置比例: {manual_stats['center_positions_ratio']:.1%}")
    print(f"  快速变化比例: {manual_stats['rapid_changes_ratio']:.1%}")
    print(f"  缓慢变化比例: {manual_stats['slow_changes_ratio']:.1%}")
    print()
    
    # 对比分析
    print("=" * 80)
    print("对比分析:")
    print("=" * 80)
    
    metrics = [
        ('总动作数', 'total_actions', ''),
        ('动作频率', 'actions_per_second', ' actions/s'),
        ('平均位置变化', 'avg_position_change', ''),
        ('极端位置比例', 'extreme_positions_ratio', '%'),
        ('中心位置比例', 'center_positions_ratio', '%'),
        ('快速变化比例', 'rapid_changes_ratio', '%'),
        ('缓慢变化比例', 'slow_changes_ratio', '%'),
    ]
    
    print(f"{'指标':<20} {'生成':<15} {'手工':<15} {'差异':<15} {'差异%':<10}")
    print("-" * 80)
    
    for name, key, unit in metrics:
        gen_val = generated_stats.get(key, 0)
        man_val = manual_stats.get(key, 0)
        diff = gen_val - man_val
        diff_pct = (diff / man_val * 100) if man_val != 0 else 0
        
        if unit == '%':
            gen_str = f"{gen_val*100:.1f}{unit}"
            man_str = f"{man_val*100:.1f}{unit}"
            diff_str = f"{diff*100:.1f}{unit}"
        else:
            gen_str = f"{gen_val:.2f}{unit}"
            man_str = f"{man_val:.2f}{unit}"
            diff_str = f"{diff:.2f}{unit}"
        
        diff_pct_str = f"{diff_pct:+.1f}%"
        
        print(f"{name:<20} {gen_str:<15} {man_str:<15} {diff_str:<15} {diff_pct_str:<10}")
    
    print()
    print("=" * 80)
    print("关键发现:")
    print("=" * 80)
    
    # 动作频率对比
    freq_diff_pct = ((generated_stats['actions_per_second'] - manual_stats['actions_per_second']) / manual_stats['actions_per_second'] * 100) if manual_stats['actions_per_second'] > 0 else 0
    print(f"1. 动作频率: 生成 {generated_stats['actions_per_second']:.2f} vs 手工 {manual_stats['actions_per_second']:.2f} ({freq_diff_pct:+.1f}%)")
    if freq_diff_pct < -30:
        print("   [警告] 动作频率明显偏低，需要进一步降低merge_threshold_ms和prominence_ratio")
    elif freq_diff_pct > 30:
        print("   [警告] 动作频率明显偏高，可能需要提高merge_threshold_ms和prominence_ratio")
    else:
        print("   [成功] 动作频率接近目标")
    
    # 中心位置比例对比
    center_diff_pct = ((generated_stats['center_positions_ratio'] - manual_stats['center_positions_ratio']) / manual_stats['center_positions_ratio'] * 100) if manual_stats['center_positions_ratio'] > 0 else 0
    print(f"2. 中心位置比例: 生成 {generated_stats['center_positions_ratio']*100:.1f}% vs 手工 {manual_stats['center_positions_ratio']*100:.1f}% ({center_diff_pct:+.1f}%)")
    if center_diff_pct < -20:
        print("   [警告] 中心位置比例偏低，需要增强位置调整逻辑")
    else:
        print("   [成功] 中心位置比例接近目标")
    
    # 极端位置比例对比
    extreme_diff_pct = ((generated_stats['extreme_positions_ratio'] - manual_stats['extreme_positions_ratio']) / manual_stats['extreme_positions_ratio'] * 100) if manual_stats['extreme_positions_ratio'] > 0 else 0
    print(f"3. 极端位置比例: 生成 {generated_stats['extreme_positions_ratio']*100:.1f}% vs 手工 {manual_stats['extreme_positions_ratio']*100:.1f}% ({extreme_diff_pct:+.1f}%)")
    if extreme_diff_pct > 50:
        print("   [警告] 极端位置比例偏高，需要增强位置调整逻辑")
    else:
        print("   [成功] 极端位置比例接近目标")
    
    # 缓慢变化比例对比
    slow_diff_pct = ((generated_stats['slow_changes_ratio'] - manual_stats['slow_changes_ratio']) / manual_stats['slow_changes_ratio'] * 100) if manual_stats['slow_changes_ratio'] > 0 else 0
    print(f"4. 缓慢变化比例: 生成 {generated_stats['slow_changes_ratio']*100:.1f}% vs 手工 {manual_stats['slow_changes_ratio']*100:.1f}% ({slow_diff_pct:+.1f}%)")
    if slow_diff_pct < -50:
        print("   [警告] 缓慢变化比例偏低，可能需要增强平滑处理")
    else:
        print("   [成功] 缓慢变化比例接近目标")

if __name__ == '__main__':
    main()

