#!/usr/bin/env python3
# Copyright (c) 2023 Max Planck Society
# License: https://bedlam.is.tuebingen.mpg.de/license.html
#
# Reads a be_seq.csv file and expands each sequence into 6 panoramic views
# (Front, Back, Left, Right, Up, Down) for 360-degree rendering.
#
# Usage:
# python be_add_pov_six_views.py <input_csv_path> <output_csv_path>
#
# Example:
# python be_add_pov_six_views.py be_seq.csv be_seq_panoramic.csv
# python be_add_pov_six_views.py be_seq_test2.csv be_seq_test2_pov_panoramic.csv

import csv
import sys
from pathlib import Path

# 定义CSV文件默认搜索路径
DEFAULT_CSV_DIRS = [
    Path('.'),  # 当前目录
    Path('./images/test/'),  # images/test 子目录
    Path('../images/test/'),  # 上级目录的 images/test
    Path('../../images/test/'),  # 两级上级目录的 images/test
]

# 定义6个全景视角的参数
PANORAMIC_VIEWS = [
    {
        'suffix': '_front',
        'view_id': 0,
        'yaw_offset': 0,      # 正前方
        'pitch_offset': 0,
        'roll_offset': 0,
        'description': 'front_view'
    },
    {
        'suffix': '_back',
        'view_id': 1,
        'yaw_offset': 180,    # 正后方
        'pitch_offset': 0,
        'roll_offset': 0,
        'description': 'back_view'
    },
    {
        'suffix': '_left',
        'view_id': 2,
        'yaw_offset': -90,    # 左侧
        'pitch_offset': 0,
        'roll_offset': 0,
        'description': 'left_view'
    },
    {
        'suffix': '_right',
        'view_id': 3,
        'yaw_offset': 90,     # 右侧
        'pitch_offset': 0,
        'roll_offset': 0,
        'description': 'right_view'
    },
    {
        'suffix': '_up',
        'view_id': 4,
        'yaw_offset': 0,
        'pitch_offset': -90,  # 向上看
        'roll_offset': 0,
        'description': 'up_view'
    },
    {
        'suffix': '_down',
        'view_id': 5,
        'yaw_offset': 0,
        'pitch_offset': 90,   # 向下看
        'roll_offset': 0,
        'description': 'down_view'
    }
]

def find_csv_file(file_path):
    """
    自动查找CSV文件的正确路径
    
    Args:
        file_path: 用户提供的文件路径（可能是相对路径或文件名）
    
    Returns:
        Path对象，找到的文件路径；如果找不到则返回None
    """
    file_path = Path(file_path)
    
    # 如果提供的路径存在，直接返回
    if file_path.exists():
        print(f"Found file at: {file_path.absolute()}")
        return file_path
    
    # 如果只提供了文件名（不含路径），在默认目录中搜索
    if len(file_path.parts) == 1:
        file_name = file_path.name
        for search_dir in DEFAULT_CSV_DIRS:
            candidate_path = search_dir / file_name
            if candidate_path.exists():
                print(f"Found file at: {candidate_path.absolute()}")
                return candidate_path
    
    # 如果提供了相对路径但不存在，也在默认目录中搜索同名文件
    file_name = file_path.name
    for search_dir in DEFAULT_CSV_DIRS:
        candidate_path = search_dir / file_name
        if candidate_path.exists():
            print(f"Found file at: {candidate_path.absolute()}")
            return candidate_path
    
    return None

def prepare_output_path(input_path, output_path):
    """
    准备输出文件路径，强制使其与输入文件在同一目录
    
    Args:
        input_path: 输入文件的Path对象
        output_path: 用户提供的输出文件路径
    
    Returns:
        Path对象，准备好的输出路径
    """
    output_path = Path(output_path)
    
    # 强制将输出文件放在与输入文件相同的目录
    # 只取输出路径的文件名，忽略用户提供的路径部分
    output_filename = output_path.name
    final_output_path = input_path.parent / output_filename
    
    print(f"Output will be saved to: {final_output_path.absolute()}")
    return final_output_path

def normalize_angle(angle):
    """将角度标准化到 [-180, 180) 范围"""
    while angle >= 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def expand_sequence_to_panoramic(group_row, body_row, view_config):
    """
    根据视角配置扩展一个序列（Group行和Body行）
    
    Args:
        group_row: Group行（字典格式）
        body_row: Body行（字典格式）
        view_config: 视角配置字典
    
    Returns:
        (new_group_row, new_body_row): 新的Group行和Body行元组
    """
    # 处理Group行
    new_group_row = group_row.copy()
    original_comment = group_row['Comment']
    
    if 'sequence_name=' in original_comment:
        # 解析并修改sequence_name：seq_000000 -> seq_000000_pov_front
        parts = original_comment.split(';')
        new_parts = []
        for part in parts:
            if part.startswith('sequence_name='):
                seq_name = part.split('=')[1]
                # 将 seq_ 替换为 seq_number_pov_
                new_seq_name = seq_name.replace('seq_', f'seq_') + f'_pov{view_config["suffix"]}'
                new_parts.append(f"sequence_name={new_seq_name}")
            elif part.startswith('camera_hfov='):
                # 修改相机FOV为90度（全景渲染标准）
                new_parts.append('camera_hfov=90')
            else:
                new_parts.append(part)
        new_group_row['Comment'] = ';'.join(new_parts)
        # 添加pov_camera和view信息
        new_group_row['Comment'] += f";pov_camera=true;view_id={view_config['view_id']};view={view_config['description']}"
    else:
        # 如果没有sequence_name，直接添加view信息
        if original_comment:
            new_group_row['Comment'] = f"{original_comment};pov_camera=true;view_id={view_config['view_id']};view={view_config['description']}"
        else:
            new_group_row['Comment'] = f"pov_camera=true;view_id={view_config['view_id']};view={view_config['description']}"
    
    # 处理Body行 - 保持Body的旋转不变，角度偏移将在相机上应用
    new_body_row = body_row.copy()
    # 不修改Body的Yaw/Pitch/Roll，保持原始朝向
    
    return new_group_row, new_body_row

def process_csv(input_path, output_path):
    """
    处理CSV文件，将每个序列扩展为6个全景视角
    
    Args:
        input_path: 输入CSV文件路径
        output_path: 输出CSV文件路径
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    # 读取输入CSV
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    print(f"Reading from: {input_path.absolute()}")
    print(f"Found {len(rows)} rows")
    
    # 分离Comment行（第0行）和序列行
    comment_row = None
    sequence_pairs = []
    
    for i, row in enumerate(rows):
        if row['Type'] == 'Comment':
            # 全局Comment行，只保留一个
            if comment_row is None:
                comment_row = row
        elif row['Type'] == 'Group':
            # Group行，找到对应的Body行
            if i + 1 < len(rows) and rows[i + 1]['Type'] == 'Body':
                sequence_pairs.append((row, rows[i + 1]))
    
    print(f"Found {len(sequence_pairs)} sequences (Group+Body pairs)")
    
    # 构建输出行
    expanded_rows = []
    
    # 首先添加全局Comment行（只添加一次，并添加view信息）
    if comment_row:
        modified_comment_row = comment_row.copy()
        original_comment = comment_row['Comment']
        # 在全局Comment中添加说明，表示这是扩展的全景视图CSV
        modified_comment_row['Comment'] = f"{original_comment};panoramic_views=6"
        expanded_rows.append(modified_comment_row)
    
    # 扩展每个序列为6个视角
    for seq_idx, (group_row, body_row) in enumerate(sequence_pairs):
        print(f"Processing sequence {seq_idx + 1}/{len(sequence_pairs)}")
        
        # 为当前序列生成所有6个视角
        for view_config in PANORAMIC_VIEWS:
            new_group_row, new_body_row = expand_sequence_to_panoramic(group_row, body_row, view_config)
            expanded_rows.append(new_group_row)
            expanded_rows.append(new_body_row)
    
    # 重新编号Index
    for idx, row in enumerate(expanded_rows):
        row['Index'] = str(idx)
    
    # 写入输出CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(expanded_rows)
    
    print(f"Writing to: {output_path.absolute()}")
    print(f"Expanded to {len(expanded_rows)} rows (1 Comment + {len(sequence_pairs)} sequences × 6 views × 2 rows)")
    print(f"Successfully created panoramic view CSV")
    
    return True

def main():
    if len(sys.argv) != 3:
        print("Usage: python be_add_pov_six_views.py <input_csv_path> <output_csv_path>")
        print("Example: python be_add_pov_six_views.py be_seq.csv be_seq_panoramic.csv")
        print("         python be_add_pov_six_views.py be_seq_test2.csv be_seq_test2_pov_panoramic.csv")
        print("\nNote: Script will automatically search for CSV files in:")
        for search_dir in DEFAULT_CSV_DIRS:
            print(f"  - {search_dir.absolute()}")
        print("\nOutput file will be saved in the same directory as the input file.")
        sys.exit(1)
    
    input_path_arg = sys.argv[1]
    output_path_arg = sys.argv[2]
    
    # 自动查找输入文件
    input_path = find_csv_file(input_path_arg)
    if not input_path:
        print(f"Error: Input file not found: {input_path_arg}")
        print("Searched in the following directories:")
        for search_dir in DEFAULT_CSV_DIRS:
            print(f"  - {search_dir.absolute()}")
        sys.exit(1)
    
    # 准备输出文件路径（强制与输入文件在同一目录）
    output_path = prepare_output_path(input_path, output_path_arg)
    
    # 处理CSV
    success = process_csv(input_path, output_path)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()