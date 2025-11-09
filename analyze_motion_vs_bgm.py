"""分析纯运动视频的funscript特征，作为重要测试参考"""
import json
import statistics
from pathlib import Path
from typing import Dict, List

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
        
        # 计算周期性特征（BGM驱动的funscript通常有更强的周期性）
        if len(intervals) > 10:
            # 分析间隔的周期性
            interval_std = statistics.stdev(intervals) if len(intervals) > 1 else 0
            interval_mean = statistics.mean(intervals) if intervals else 0
            interval_cv = interval_std / interval_mean if interval_mean > 0 else 0  # 变异系数
            
            # 分析位置变化的周期性
            change_std = statistics.stdev(position_changes) if len(position_changes) > 1 else 0
            change_mean = statistics.mean(position_changes) if position_changes else 0
            change_cv = change_std / change_mean if change_mean > 0 else 0
        else:
            interval_cv = 0
            change_cv = 0
        
        return {
            'total_actions': len(actions),
            'duration_ms': timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0,
            'avg_interval_ms': statistics.mean(intervals) if intervals else 0,
            'interval_std_ms': statistics.stdev(intervals) if len(intervals) > 1 else 0,
            'interval_cv': interval_cv,  # 变异系数：越小越规律（BGM特征）
            'actions_per_second': len(actions) / ((timestamps[-1] - timestamps[0]) / 1000.0) if len(timestamps) > 1 and timestamps[-1] > timestamps[0] else 0,
            'avg_position_change': statistics.mean(position_changes) if position_changes else 0,
            'change_std': change_std if len(position_changes) > 1 else 0,
            'change_cv': change_cv,  # 位置变化的变异系数
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
    print("纯运动视频（无BGM）funscript特征分析")
    print("=" * 80)
    print(f"视频: {VIDEO_NAME}")
    print()
    
    # 分析所有手工制作的funscript文件
    manual_axes = ['pitch', 'roll', 'surge', 'sway', 'twist']
    all_manual_stats = []
    
    for axis in manual_axes:
        funscript_path = BASE_DIR / f"{VIDEO_NAME}.{axis}.funscript"
        if funscript_path.exists():
            print(f"分析 {axis} 轴:")
            print("-" * 80)
            stats = analyze_funscript(funscript_path)
            if stats:
                stats['axis'] = axis
                all_manual_stats.append(stats)
                
                print(f"  总动作数: {stats['total_actions']}")
                print(f"  时长: {stats['duration_ms']/1000:.1f}秒")
                print(f"  平均间隔: {stats['avg_interval_ms']:.1f}ms")
                print(f"  间隔标准差: {stats['interval_std_ms']:.1f}ms")
                print(f"  间隔变异系数: {stats['interval_cv']:.3f} (越小越规律，BGM特征)")
                print(f"  动作频率: {stats['actions_per_second']:.2f} actions/s")
                print(f"  平均位置变化: {stats['avg_position_change']:.2f}")
                print(f"  位置变化变异系数: {stats['change_cv']:.3f}")
                print(f"  极端位置比例: {stats['extreme_positions_ratio']:.1%}")
                print(f"  中心位置比例: {stats['center_positions_ratio']:.1%}")
                print(f"  快速变化比例: {stats['rapid_changes_ratio']:.1%}")
                print(f"  缓慢变化比例: {stats['slow_changes_ratio']:.1%}")
                print()
    
    if not all_manual_stats:
        print("未找到手工制作的funscript文件")
        return
    
    # 计算平均值
    print("=" * 80)
    print("所有轴的平均特征（运动驱动的funscript特征）:")
    print("=" * 80)
    
    avg_stats = {}
    for key in all_manual_stats[0].keys():
        if key == 'axis':
            continue
        if isinstance(all_manual_stats[0][key], (int, float)):
            avg_stats[key] = statistics.mean([s[key] for s in all_manual_stats])
    
    print(f"平均动作数: {avg_stats.get('total_actions', 0):.0f}")
    print(f"平均时长: {avg_stats.get('duration_ms', 0)/1000:.1f}秒")
    print(f"平均间隔: {avg_stats.get('avg_interval_ms', 0):.1f}ms")
    print(f"间隔变异系数: {avg_stats.get('interval_cv', 0):.3f} (运动驱动通常>0.3，BGM驱动通常<0.2)")
    print(f"平均动作频率: {avg_stats.get('actions_per_second', 0):.2f} actions/s")
    print(f"平均位置变化: {avg_stats.get('avg_position_change', 0):.2f}")
    print(f"位置变化变异系数: {avg_stats.get('change_cv', 0):.3f} (运动驱动通常>0.5，BGM驱动通常<0.3)")
    print(f"极端位置比例: {avg_stats.get('extreme_positions_ratio', 0):.1%}")
    print(f"中心位置比例: {avg_stats.get('center_positions_ratio', 0):.1%}")
    print(f"快速变化比例: {avg_stats.get('rapid_changes_ratio', 0):.1%}")
    print(f"缓慢变化比例: {avg_stats.get('slow_changes_ratio', 0):.1%}")
    print()
    
    # 判断特征
    print("=" * 80)
    print("特征判断:")
    print("=" * 80)
    
    interval_cv = avg_stats.get('interval_cv', 0)
    change_cv = avg_stats.get('change_cv', 0)
    
    if interval_cv > 0.3 and change_cv > 0.5:
        print("[运动驱动] 判断：运动驱动的funscript（符合工具目标）")
        print("   - 间隔变异系数较高，说明动作间隔不规律（跟随运动）")
        print("   - 位置变化变异系数较高，说明变化幅度不规律（跟随运动）")
    elif interval_cv < 0.2 and change_cv < 0.3:
        print("[BGM驱动] 判断：BGM驱动的funscript（不符合工具目标）")
        print("   - 间隔变异系数较低，说明动作间隔规律（跟随节拍）")
        print("   - 位置变化变异系数较低，说明变化幅度规律（跟随节拍）")
    else:
        print("[混合特征] 判断：混合特征（可能同时受运动和BGM影响）")
    
    print()
    print("=" * 80)
    print("建议:")
    print("=" * 80)
    print("1. 这个视频的funscript特征应该作为工具优化的目标")
    print("2. 如果其他视频的funscript特征与此差异很大，可能是BGM驱动的")
    print("3. 推荐算法应该优先匹配运动驱动的funscript特征")
    print("4. 可以考虑添加周期性检测，过滤掉BGM驱动的参考funscript")

if __name__ == '__main__':
    main()

