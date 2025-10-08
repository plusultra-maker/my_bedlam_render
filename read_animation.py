import numpy as np
import os

def check_npz_frames(npz_path):
    """
    检查NPZ文件中poses数组包含的帧数
    
    Args:
        npz_path: NPZ文件的路径
    
    Returns:
        帧数信息字典
    """
    try:
        # 加载NPZ文件
        data = np.load(npz_path, allow_pickle=True)
        
        print(f"文件: {npz_path}")
        print(f"包含的键: {list(data.keys())}")
        print("-" * 50)
        
        # 检查每个数组的形状
        for key in data.keys():
            arr = data[key]
            print(f"{key}:")
            print(f"  形状: {arr.shape}")
            print(f"  数据类型: {arr.dtype}")
            
            # 如果是poses数组，第一维通常是帧数
            if key == 'poses':
                num_frames = arr.shape[0]
                print(f"  帧数: {num_frames}")
                if len(arr.shape) > 1:
                    print(f"  每帧参数数量: {arr.shape[1]}")
            
            print()
        
        return {
            'num_frames': data['poses'].shape[0] if 'poses' in data else None,
            'pose_params_per_frame': data['poses'].shape[1] if 'poses' in data and len(data['poses'].shape) > 1 else None
        }
        
    except Exception as e:
        print(f"错误: {e}")
        return None

if __name__ == "__main__":
    # 您的NPZ文件路径 female_37_nl_5702_0011
    npz_file = r"E:\CS\Graphics\bedlam_render\animations\gt_part1_male_female\female_37_nl_5702\moving_body_para\0011\motion_seq.npz"
    
    # 检查文件是否存在
    if not os.path.exists(npz_file):
        print(f"文件不存在: {npz_file}")
    else:
        result = check_npz_frames(npz_file)
        
        if result and result['num_frames']:
            print("=" * 50)
            print(f"总结: 该文件包含 {result['num_frames']} 帧")
            if result['pose_params_per_frame']:
                print(f"每帧有 {result['pose_params_per_frame']} 个pose参数")