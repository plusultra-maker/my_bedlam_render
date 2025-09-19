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
#   python cubemap2equirectangular.py --input_dir /path/to/cubemaps --output_dir /path/to/output
#

import os
import cv2
import numpy as np
import py360convert
import argparse
from collections import defaultdict
import re

# ------------------- 可配置参数 -------------------
# 您可以根据需要修改这些默认值，或通过命令行参数覆盖它们。

# 1. 立方图面与文件/文件夹后缀的映射关系
#    py360convert 需要知道哪个文件对应哪个面 ('F', 'B', 'U', 'D', 'R', 'L')
#    这里的数字 '1' 对应文件夹 'seq_pov_1' 和文件名 'seq_pov_1_xxxx.png'
DEFAULT_CUBE_MAP = {
    '1': 'F',  # Front (+X)
    '2': 'R',
    '3': 'B',
    '4': 'L',
    '5': 'U',
    '6': 'D'   # Down (-Y)
}

# 2. 输出全景图的高度
DEFAULT_EQUI_HEIGHT = 1024

# 3. 输出全景图的宽度
DEFAULT_EQUI_WIDTH = 2048

# 4. 图像文件扩展名
DEFAULT_IMG_EXTENSION = '.png'

# 5. 包含视角图像的子文件夹名称格式
#    {pov_index} 会被替换为 DEFAULT_CUBE_MAP 中的键 (1, 2, 3...)
POV_DIR_FORMAT = 'seq_pov_{pov_index}'
# ----------------------------------------------------


def convert_cubemaps_to_equirectangular(input_dir, output_dir, cube_map_config, height, width, ext):
    """
    Scans a directory with a specific subfolder structure for cubemap images,
    groups them by frame, and converts each group into an equirectangular image.
    """
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at '{input_dir}'")
        return

    if not os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' not found. Creating it.")
        os.makedirs(output_dir)

    # 按时间帧编号对图像路径进行分组
    frames = defaultdict(dict)
    print(f"Scanning for images in '{input_dir}'...")

    # 遍历每个视角的子文件夹
    for pov_index, face in cube_map_config.items():
        pov_dir_name = POV_DIR_FORMAT.format(pov_index=pov_index)
        current_dir = os.path.join(input_dir, pov_dir_name)

        if not os.path.isdir(current_dir):
            print(f"Warning: POV directory '{current_dir}' not found. Skipping.")
            continue

        # 遍历文件夹中的每个文件
        for filename in os.listdir(current_dir):
            # 使用正则表达式从文件名中提取帧编号 (例如从 'seq_pov_1_0015.png' 中提取 '0015')
            match = re.search(r'_(\d+)' + re.escape(ext) + '$', filename)
            if match:
                frame_number = match.group(1)
                frames[frame_number][face] = os.path.join(current_dir, filename)

    print(f"Found {len(frames)} potential frames.")

    # 处理每个找到的时间帧
    for frame_number, face_paths in frames.items():
        if len(face_paths) == 6:
            print(f"Processing frame: {frame_number}")
            try:
                # 读取六个面的图像
                cube_faces = {
                    face: cv2.imread(path) for face, path in face_paths.items()
                }

                # 检查所有图像是否成功读取
                if any(img is None for img in cube_faces.values()):
                    print(f"  - Error: Could not read one or more images for frame '{frame_number}'. Skipping.")
                    continue

                # 使用 py360convert 进行转换
                equi_img = py360convert.c2e(cube_faces, h=height, w=width, mode='bilinear', cube_format='dict')

                # 保存结果
                output_filename = f"frame_{frame_number}_equirectangular{ext}"
                output_path = os.path.join(output_dir, output_filename)
                cv2.imwrite(output_path, equi_img)
                print(f"  - Successfully converted and saved to '{output_path}'")

            except Exception as e:
                print(f"  - Error processing frame '{frame_number}': {e}")
        else:
            print(f"  - Warning: Skipping frame '{frame_number}' as it does not have all 6 faces. Found {len(face_paths)}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert cubemap images from a structured directory to equirectangular panoramas.'
    )
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Root directory containing the POV subfolders (e.g., seq_pov_1, seq_pov_2, ...).'
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
        args.ext
    )
    
# python e:\CS\Graphics\bedlam_render\tools\post_render_pipeline\cubemap2equirectangular.py --input_dir E:\CS\Graphics\bedlam_render\images\test\test_1 --output_dir E:\CS\Graphics\bedlam_render\images\test\equirectangular_output_1