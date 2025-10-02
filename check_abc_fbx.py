#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查ABC和FBX文件夹的文件差异
比较两个目录下的文件，找出缺失的文件并记录到报告中
"""

import os
from pathlib import Path
from collections import defaultdict
import re

def extract_subject_and_frame(file_path, file_type):
    """
    从文件路径中提取subject名称和帧号
    
    Args:
        file_path: Path对象，文件路径
        file_type: str, 'abc' 或 'fbx'
    
    Returns:
        tuple: (subject_name, frame_number) 或 None
    """
    if file_type == 'abc':
        # ABC: subject_folder/subject_name_frame.abc
        if file_path.suffix == '.abc':
            subject_folder = file_path.parent.name
            file_name = file_path.stem
            
            # 尝试匹配 subject_name_frame 格式
            match = re.match(r'(.+)_(\d+)$', file_name)
            if match:
                subject_name = match.group(1)
                frame_number = match.group(2)
                return (subject_name, frame_number)
    
    elif file_type == 'fbx':
        # FBX: 假设类似的结构
        if file_path.suffix == '.fbx':
            subject_folder = file_path.parent.name if file_path.parent.name != 'fbx' else None
            file_name = file_path.stem
            
            # 如果FBX文件直接在fbx目录下，从文件名提取
            if subject_folder is None or subject_folder == 'fbx':
                # 假设格式类似 subject_name_frame.fbx 或 subject_name.fbx
                match = re.match(r'(.+?)(?:_(\d+))?$', file_name)
                if match:
                    subject_name = match.group(1)
                    frame_number = match.group(2) if match.group(2) else '0000'
                    return (subject_name, frame_number)
            else:
                # 如果有子文件夹结构
                match = re.match(r'(.+)_(\d+)$', file_name)
                if match:
                    subject_name = match.group(1)
                    frame_number = match.group(2)
                    return (subject_name, frame_number)
    
    return None

def scan_directory(directory, file_type):
    """
    扫描目录并提取所有相关文件信息
    
    Args:
        directory: str, 目录路径
        file_type: str, 'abc' 或 'fbx'
    
    Returns:
        dict: {(subject_name, frame_number): file_path}
    """
    files_dict = {}
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"警告: 目录 {directory} 不存在")
        return files_dict
    
    # 递归搜索所有相关文件
    if file_type == 'abc':
        pattern = "**/*.abc"
    else:
        pattern = "**/*.fbx"
    
    for file_path in directory_path.rglob(pattern):
        result = extract_subject_and_frame(file_path, file_type)
        if result:
            subject_name, frame_number = result
            key = (subject_name, frame_number)
            files_dict[key] = file_path
    
    return files_dict

def generate_report(abc_files, fbx_files, output_file):
    """
    生成差异报告
    """
    abc_keys = set(abc_files.keys())
    fbx_keys = set(fbx_files.keys())
    
    # 找出所有的subject
    all_subjects = set()
    for subject, frame in abc_keys | fbx_keys:
        all_subjects.add(subject)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ABC 和 FBX 文件差异报告\n")
        f.write("=" * 80 + "\n\n")
        
        # 总体统计
        f.write("总体统计:\n")
        f.write(f"ABC 文件总数: {len(abc_files)}\n")
        f.write(f"FBX 文件总数: {len(fbx_files)}\n")
        f.write(f"共同的 subject 数量: {len(all_subjects)}\n\n")
        
        # 只在ABC中存在的文件
        only_abc = abc_keys - fbx_keys
        f.write(f"只在ABC中存在的文件 ({len(only_abc)} 个):\n")
        f.write("-" * 50 + "\n")
        if only_abc:
            # 按subject分组
            abc_only_by_subject = defaultdict(list)
            for subject, frame in sorted(only_abc):
                abc_only_by_subject[subject].append(frame)
            
            for subject in sorted(abc_only_by_subject.keys()):
                frames = sorted(abc_only_by_subject[subject])
                f.write(f"  {subject}: {len(frames)} 个文件\n")
                f.write(f"    帧号: {', '.join(frames)}\n")
                f.write(f"    路径示例: {abc_files[(subject, frames[0])]}\n\n")
        else:
            f.write("  无\n\n")
        
        # 只在FBX中存在的文件
        only_fbx = fbx_keys - abc_keys
        f.write(f"只在FBX中存在的文件 ({len(only_fbx)} 个):\n")
        f.write("-" * 50 + "\n")
        if only_fbx:
            # 按subject分组
            fbx_only_by_subject = defaultdict(list)
            for subject, frame in sorted(only_fbx):
                fbx_only_by_subject[subject].append(frame)
            
            for subject in sorted(fbx_only_by_subject.keys()):
                frames = sorted(fbx_only_by_subject[subject])
                f.write(f"  {subject}: {len(frames)} 个文件\n")
                f.write(f"    帧号: {', '.join(frames)}\n")
                f.write(f"    路径示例: {fbx_files[(subject, frames[0])]}\n\n")
        else:
            f.write("  无\n\n")
        
        # 共同存在的文件
        common_files = abc_keys & fbx_keys
        f.write(f"同时存在于ABC和FBX中的文件 ({len(common_files)} 个):\n")
        f.write("-" * 50 + "\n")
        if common_files:
            # 按subject分组
            common_by_subject = defaultdict(list)
            for subject, frame in sorted(common_files):
                common_by_subject[subject].append(frame)
            
            for subject in sorted(common_by_subject.keys()):
                frames = sorted(common_by_subject[subject])
                f.write(f"  {subject}: {len(frames)} 个文件\n")
        else:
            f.write("  无\n\n")
        
        # 按subject的详细分析
        f.write("\n" + "=" * 80 + "\n")
        f.write("按 Subject 详细分析:\n")
        f.write("=" * 80 + "\n\n")
        
        for subject in sorted(all_subjects):
            # 获取该subject的所有ABC和FBX文件
            subject_abc = {frame for subj, frame in abc_keys if subj == subject}
            subject_fbx = {frame for subj, frame in fbx_keys if subj == subject}
            
            f.write(f"Subject: {subject}\n")
            f.write(f"  ABC 文件数: {len(subject_abc)}\n")
            f.write(f"  FBX 文件数: {len(subject_fbx)}\n")
            
            if subject_abc and subject_fbx:
                f.write(f"  共同帧数: {len(subject_abc & subject_fbx)}\n")
                
                abc_only_frames = subject_abc - subject_fbx
                if abc_only_frames:
                    f.write(f"  只有ABC的帧: {', '.join(sorted(abc_only_frames))}\n")
                
                fbx_only_frames = subject_fbx - subject_abc
                if fbx_only_frames:
                    f.write(f"  只有FBX的帧: {', '.join(sorted(fbx_only_frames))}\n")
            
            elif subject_abc:
                f.write(f"  只存在ABC文件，帧号: {', '.join(sorted(subject_abc))}\n")
            elif subject_fbx:
                f.write(f"  只存在FBX文件，帧号: {', '.join(sorted(subject_fbx))}\n")
            
            f.write("\n")

def main():
    # 配置路径
    abc_directory = "C:/Users/98391/Desktop/Boyang/my_bedlam_render/abc"
    fbx_directory = "C:/Users/98391/Desktop/Boyang/my_bedlam_render/fbx"
    output_file = "C:/Users/98391/Desktop/Boyang/my_bedlam_render/file_differences_report.txt"
    
    print("开始扫描文件...")
    
    # 扫描ABC文件
    print("扫描ABC文件...")
    abc_files = scan_directory(abc_directory, 'abc')
    print(f"找到 {len(abc_files)} 个ABC文件")
    
    # 扫描FBX文件
    print("扫描FBX文件...")
    fbx_files = scan_directory(fbx_directory, 'fbx')
    print(f"找到 {len(fbx_files)} 个FBX文件")
    
    # 生成报告
    print("生成差异报告...")
    generate_report(abc_files, fbx_files, output_file)
    
    print(f"报告已生成: {output_file}")
    
    # 简要打印到控制台
    abc_keys = set(abc_files.keys())
    fbx_keys = set(fbx_files.keys())
    
    print("\n简要统计:")
    print(f"ABC文件总数: {len(abc_files)}")
    print(f"FBX文件总数: {len(fbx_files)}")
    print(f"只在ABC中: {len(abc_keys - fbx_keys)}")
    print(f"只在FBX中: {len(fbx_keys - abc_keys)}")
    print(f"共同存在: {len(abc_keys & fbx_keys)}")

if __name__ == "__main__":
    main()