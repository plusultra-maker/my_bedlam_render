# -*- coding: utf-8 -*-
#
# Copyright (c) 2023 Max Planck Society
# License: https://bedlam.is.tuebingen.mpg.de/license.html
#
# This script converts a set of 6 cubemap face images into an equirectangular panorama.
# It processes an input directory, finds image sets, and uses the py360convert library for the conversion.
#
# Requirements:
#   pip install numpy opencv-python py360convert
#
# Example Usage:
#   python cubemap2equirectangular.py --input_dir E:\CS\Graphics\bedlam_render\images\test\png --output_dir E:\CS\Graphics\bedlam_render\images\test\equirectangular_output
#

import os
import cv2
import numpy as np
import py360convert
import argparse
from collections import defaultdict
import re

# ------------------- 可配置参数 -------------------

# 1. 立方图面与视角名称的映射关系
#    py360convert 需要知道哪个视角对应哪个面 ('F', 'B', 'U', 'D', 'R', 'L')
DEFAULT_CUBE_MAP = {
    'front': 'F',  # Front
    'right': 'R',  # Right
    'back': 'B',   # Back
    'left': 'L',   # Left
    'up': 'U',     # Up
    'down': 'D'    # Down
}

# 2. 输出全景图的高度
DEFAULT_EQUI_HEIGHT = 1024

# 3. 输出全景图的宽度
DEFAULT_EQUI_WIDTH = 2048

# 4. 图像文件扩展名
DEFAULT_IMG_EXTENSION = '.png'

# 5. 包含视角图像的子文件夹名称格式
#    格式: seq_{seq_num}_pov_{view_name}
POV_DIR_PATTERN = re.compile(r'seq_(\d+)_pov_(\w+)$')

# 6. 图像文件名格式
#    格式: seq_{seq_num}_pov_{view_name}_{frame_num}.png
IMG_FILENAME_PATTERN = re.compile(r'seq_\d+_pov_\w+_(-?\d+)\.png$')

# 7. 是否进行中心裁剪为正方形
CROP_TO_SQUARE = True

# 8. 裁剪时边缘留出的像素（避免黑边）
CROP_MARGIN = 1

# ----------------------------------------------------


def crop_center_square(img, margin=1):
    """
    从图像中心裁剪出正方形区域
    
    Args:
        img: 输入图像 (numpy array)
        margin: 裁剪时减少的像素数，避免黑边 (default: 1)
    
    Returns:
        裁剪后的正方形图像
    """
    h, w = img.shape[:2]
    
    # 使用高度作为正方形边长（减去margin避免黑边）
    square_size = h - margin
    
    # 计算中心裁剪的起始位置
    # 在宽度方向上居中
    start_x = (w - square_size) // 2
    start_y = margin // 2  # 如果高度也需要调整
    
    # 裁剪
    cropped = img[start_y:start_y + square_size, start_x:start_x + square_size]
    
    return cropped


def convert_cubemaps_to_equirectangular(input_dir, output_dir, cube_map_config, height, width, ext, crop_square=True, crop_margin=1):
    """
    Scans a directory with POV subfolders for cubemap images,
    groups them by sequence and frame, and converts each group into an equirectangular image.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at '{input_dir}'")
        return

    if not os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' not found. Creating it.")
        os.makedirs(output_dir)

    # 数据结构: {seq_num: {frame_num: {face: path}}}
    sequences = defaultdict(lambda: defaultdict(dict))
    
    print(f"Scanning for images in '{input_dir}'...")

    # 遍历所有子文件夹
    for dirname in os.listdir(input_dir):
        dir_path = os.path.join(input_dir, dirname)
        
        # 只处理目录
        if not os.path.isdir(dir_path):
            continue
        
        # 匹配文件夹名称: seq_000000_pov_back
        match = POV_DIR_PATTERN.match(dirname)
        if not match:
            continue
        
        seq_num = match.group(1)  # '000000'
        view_name = match.group(2)  # 'back'
        
        # 检查视角名称是否在映射中
        if view_name not in cube_map_config:
            print(f"Warning: Unknown view name '{view_name}' in directory '{dirname}'. Skipping.")
            continue
        
        face = cube_map_config[view_name]
        
        # 遍历文件夹中的所有图像
        for filename in os.listdir(dir_path):
            if not filename.lower().endswith(ext):
                continue
            
            # 从文件名中提取帧编号
            img_match = IMG_FILENAME_PATTERN.match(filename)
            if img_match:
                frame_num = img_match.group(1)  # '-0005', '0000', '0005' 等
                image_path = os.path.join(dir_path, filename)
                sequences[seq_num][frame_num][face] = image_path

    print(f"Found {len(sequences)} sequences.")

    # 处理每个序列的每个帧
    total_converted = 0
    for seq_num in sorted(sequences.keys()):
        frames = sequences[seq_num]
        print(f"\nProcessing sequence: seq_{seq_num} ({len(frames)} frames)")
        
        for frame_num in sorted(frames.keys()):
            face_paths = frames[frame_num]
            
            # 检查是否有完整的6个面
            if len(face_paths) != 6:
                print(f"  - Warning: Skipping seq_{seq_num} frame {frame_num}: only {len(face_paths)}/6 faces found.")
                continue
            
            try:
                # 读取六个面的图像
                cube_faces = {}
                all_loaded = True
                
                for face, path in face_paths.items():
                    img = cv2.imread(path)
                    if img is None:
                        print(f"  - Error: Could not read image '{path}'. Skipping frame.")
                        all_loaded = False
                        break
                    
                    # 预处理：裁剪为正方形
                    if crop_square:
                        img = crop_center_square(img, margin=crop_margin)
                    
                    cube_faces[face] = img
                
                if not all_loaded:
                    continue

                # 使用 py360convert 进行转换
                equi_img = py360convert.c2e(cube_faces, h=height, w=width, mode='bilinear', cube_format='dict')

                # 保存结果
                # 输出文件名: seq_000000_frame_0005_equirectangular.png
                output_filename = f"seq_{seq_num}_frame_{frame_num}_equirectangular{ext}"
                output_path = os.path.join(output_dir, output_filename)
                cv2.imwrite(output_path, equi_img)
                total_converted += 1
                
                if total_converted % 10 == 0:
                    print(f"  - Converted {total_converted} frames...")

            except Exception as e:
                print(f"  - Error processing seq_{seq_num} frame {frame_num}: {e}")

    print(f"\n{'='*50}")
    print(f"Conversion complete! Total frames converted: {total_converted}")
    print(f"Output directory: {output_dir}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert cubemap images from POV subfolders to equirectangular panoramas.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Root directory containing the POV subfolders (e.g., seq_000000_pov_front, seq_000000_pov_back, ...).'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Directory where the output equirectangular images will be saved.'
    )
    parser.add_argument(
        '--height',
        type=int,
        default=DEFAULT_EQUI_HEIGHT,
        help=f'Height of the output equirectangular image. Default is {DEFAULT_EQUI_HEIGHT}.'
    )
    parser.add_argument(
        '--width',
        type=int,
        default=DEFAULT_EQUI_WIDTH,
        help=f'Width of the output equirectangular image. Default is {DEFAULT_EQUI_WIDTH}.'
    )
    parser.add_argument(
        '--ext',
        type=str,
        default=DEFAULT_IMG_EXTENSION,
        help=f'Image file extension (e.g., .png, .jpg). Default is "{DEFAULT_IMG_EXTENSION}".'
    )
    parser.add_argument(
        '--no-crop',
        action='store_true',
        help='Disable center square cropping of input images.'
    )
    parser.add_argument(
        '--crop-margin',
        type=int,
        default=CROP_MARGIN,
        help=f'Margin to reduce when cropping to avoid black edges. Default is {CROP_MARGIN}.'
    )

    args = parser.parse_args()

    # 确保扩展名以点开头
    if not args.ext.startswith('.'):
        args.ext = '.' + args.ext

    convert_cubemaps_to_equirectangular(
        args.input_dir,
        args.output_dir,
        DEFAULT_CUBE_MAP,
        args.height,
        args.width,
        args.ext,
        crop_square=not args.no_crop,
        crop_margin=args.crop_margin
    )

# 使用示例:
# python e:\CS\Graphics\bedlam_render\tools\post_render_pipeline\cubemap2equirectangular.py --input_dir E:\CS\Graphics\bedlam_render\images\test\png --output_dir E:\CS\Graphics\bedlam_render\images\test\equirectangular_output
# 如果不需要裁剪，添加 --no-crop 参数
# 调整裁剪边距: --crop-margin 2