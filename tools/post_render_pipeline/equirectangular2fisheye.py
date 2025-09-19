# -*- coding: utf-8 -*-
#
# This script is based on the OmniCV library documentation.
# License: https://github.com/Kaustubh-Sadekar/OmniCV-Lib/blob/master/LICENSE
#
# This script converts an equirectangular image into a fisheye image using
# one of several available camera models from the omnicv library.
#
# Requirements:
#   pip install opencv-python omnicv
#
# Example Usage:
#   python equirectangular2fisheye.py --input_dir /path/to/equi_images --output_dir /path/to/output --model UCM --xi 1.2
#   python equirectangular2fisheye.py --input_dir /path/to/equi_images --output_dir /path/to/output --model FOV --f 40 --w 0.5
#

import os
import cv2
import argparse
from omnicv import fisheyeImgConv

# ------------------- 可配置的相机模型和参数 -------------------
#
# omnicv 提供了四种不同的相机模型，用于将等距柱状投影图转换为鱼眼图。
# 每种模型都有自己的一套参数来控制鱼眼效果的几何形状。
#
# 1. Unified Camera Model (UCM) - 统一相机模型
#    - f:  焦距 (Focal Length)。控制鱼眼图像的缩放/视野大小。
#    - xi: 畸变系数 (Distortion coefficient)。关键参数，控制鱼眼效果的强度。
#
# 2. Extended Unified Camera Model (EUCM) - 扩展统一相机模型
#    - f:  焦距 (Focal Length)。
#    - a:  畸变系数 a (Distortion coefficient a)。
#    - b:  畸变系数 b (Distortion coefficient b)。
#
# 3. Field Of View (FOV) Camera Model - 视场相机模型
#    - f:  焦距 (Focal Length)。
#    - w:  畸变系数 w (Distortion coefficient w)。
#
# 4. Double Sphere (DS) Camera Model - 双球面相机模型
#    - f:  焦距 (Focal Length)。
#    - a:  畸变系数 a (Distortion coefficient a)。
#    - xi: 畸变系数 xi (Distortion coefficient xi)。
#
# 通用参数 (适用于所有模型):
#    - outShape: 输出鱼眼图像的尺寸 [高度, 宽度]。
#    - angles:   相机的旋转角度 [roll, pitch, yaw]，单位为度。用于模拟不同方向的观察。
#
# --------------------------------------------------------------------

def convert_equirectangular_to_fisheye(args):
    """
    Scans a directory for equirectangular images and converts them to
    fisheye images using the specified model and parameters.
    """
    input_dir = args.input_dir
    output_dir = args.output_dir
    model_name = args.model.upper()

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found at '{input_dir}'")
        return

    if not os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' not found. Creating it.")
        os.makedirs(output_dir)

    # 创建 mapper 对象
    try:
        mapper = fisheyeImgConv()
    except Exception as e:
        print(f"Error: Failed to initialize omnicv.fisheyeImgConv. Is omnicv installed? Error: {e}")
        print("Please run: pip install omnicv")
        return

    print(f"Scanning for images in '{input_dir}'...")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            input_path = os.path.join(input_dir, filename)
            print(f"Processing image: {filename}")

            try:
                # 读取输入图像
                equi_img = cv2.imread(input_path)
                if equi_img is None:
                    print(f"  - Warning: Could not read image '{filename}'. Skipping.")
                    continue

                # 根据选择的模型调用相应的转换函数
                fisheye_img = None
                if model_name == 'UCM':
                    fisheye_img = mapper.equirect2Fisheye_UCM(
                        equi_img, outShape=args.out_shape, f=args.f, xi=args.xi, angles=args.angles
                    )
                elif model_name == 'EUCM':
                    fisheye_img = mapper.equirect2Fisheye_EUCM(
                        equi_img, outShape=args.out_shape, f=args.f, a_=args.a, b_=args.b, angles=args.angles
                    )
                elif model_name == 'FOV':
                    fisheye_img = mapper.equirect2Fisheye_FOV(
                        equi_img, outShape=args.out_shape, f=args.f, w_=args.w, angles=args.angles
                    )
                elif model_name == 'DS':
                    fisheye_img = mapper.equirect2Fisheye_DS(
                        equi_img, outShape=args.out_shape, f=args.f, a_=args.a, xi_=args.xi_ds, angles=args.angles
                    )
                else:
                    print(f"  - Error: Unknown model '{model_name}'. Skipping.")
                    continue

                # 保存结果
                base_name, ext = os.path.splitext(filename)
                output_filename = f"{base_name}_fisheye_{model_name}{ext}"
                output_path = os.path.join(output_dir, output_filename)
                cv2.imwrite(output_path, fisheye_img)
                print(f"  - Successfully converted and saved to '{output_path}'")

            except Exception as e:
                print(f"  - Error processing image '{filename}': {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert equirectangular images to fisheye images using omnicv.',
        formatter_class=argparse.RawTextHelpFormatter
    )

    # --- I/O Arguments ---
    parser.add_argument('--input_dir', type=str, required=True, help='Directory containing the equirectangular images.')
    parser.add_argument('--output_dir', type=str, required=True, help='Directory where the output fisheye images will be saved.')

    # --- Model Selection ---
    parser.add_argument(
        '--model',
        type=str,
        default='UCM',
        choices=['UCM', 'EUCM', 'FOV', 'DS'],
        help='The camera model to use for conversion.\n'
             'UCM: Unified Camera Model\n'
             'EUCM: Extended Unified Camera Model\n'
             'FOV: Field Of View Model\n'
             'DS: Double Sphere Model\n'
             'Default is UCM.'
    )

    # --- Common Parameters ---
    parser.add_argument('--out_shape', type=int, nargs=2, default=[250, 250], metavar=('HEIGHT', 'WIDTH'), help='Output fisheye image shape [Height, Width]. Default: 250 250.')
    parser.add_argument('--angles', type=float, nargs=3, default=[0, 0, 0], metavar=('ROLL', 'PITCH', 'YAW'), help='Camera rotation angles [roll, pitch, yaw] in degrees. Default: 0 0 0.')
    parser.add_argument('--f', type=float, default=50.0, help='Focal length. Used by all models. Default: 50.0.')

    # --- Model-Specific Parameters ---
    parser.add_argument('--xi', type=float, default=1.2, help='Distortion coefficient for UCM model. Default: 1.2.')
    parser.add_argument('--a', type=float, default=0.5, help='Distortion coefficient "a" for EUCM and DS models. Default: 0.5.')
    parser.add_argument('--b', type=float, default=0.5, help='Distortion coefficient "b" for EUCM model. Default: 0.5.')
    parser.add_argument('--w', type=float, default=0.5, help='Distortion coefficient "w" for FOV model. Default: 0.5.')
    parser.add_argument('--xi_ds', type=float, default=0.5, help='Distortion coefficient "xi" for DS model. Default: 0.5.')

    args = parser.parse_args()
    convert_equirectangular_to_fisheye(args)

# python e:\CS\Graphics\bedlam_render\tools\post_render_pipeline\equirectangular2fisheye.py --input_dir E:\CS\Graphics\bedlam_render\images\test\equirectangular_output --output_dir E:\CS\Graphics\bedlam_render\images\test\fisheye_output --model FOV --out_shape 1024 1024 --f 326 --w 1.0 --angles 0 0 225