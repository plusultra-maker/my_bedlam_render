# Copyright (c) 2023 Max Planck Society  
# License: https://bedlam.is.tuebingen.mpg.de/license.html
#
# Import SMPL-X Alembic ABC files as SkeletalMesh (for POV camera attachment)
#

import math
from pathlib import Path
import sys
import time
import unreal

# --- 配置区 ---
data_root = r"E:\CS\Graphics\bedlam_render\abc"
data_root_unreal = "/Engine/PS/Bedlam/SMPLX_Skeletal/"
# 粘贴你手动导入后生成的骨架的引用路径
smplx_skeleton_path = "/Engine/PS/Bedlam/SMPLX_Skeletal/rp_aaron_posed_002/rp_aaron_posed_002_1000_Skeleton.rp_aaron_posed_002_1000_Skeleton"

def import_abc(data_root, data_root_unreal, current_batch, num_batches, whitelist_subjects=None, whitelist_animations=None):
    # Build import list
    import_abc_paths = sorted(Path(data_root).rglob("*.abc"))

    if current_batch is not None:
        section_length = math.ceil(len(import_abc_paths)/num_batches)
        start_index = current_batch * section_length
        end_index = start_index + section_length
        if end_index > len(import_abc_paths):
            end_index = len(import_abc_paths)
        print(f"Processing section: {current_batch}, total sections: {num_batches}, range: [{start_index}:{end_index}]")
        import_abc_paths = import_abc_paths[start_index : end_index]

    for import_abc_path in import_abc_paths:
        unreal.log(f"Processing Alembic: {import_abc_path}")

        uasset_folder_name = import_abc_path.parent.name
        uasset_folder = f"{data_root_unreal}/{uasset_folder_name}"
        uasset_name = import_abc_path.stem + "_skel"
        uasset_path = f"{uasset_folder}/{uasset_name}"

        if unreal.EditorAssetLibrary.does_asset_exist(uasset_path):
            unreal.log("  Skipping import. Already imported: " + uasset_path)
        else:
            unreal.log("  Importing: " + uasset_path)

            # 1. 创建导入任务和选项，结构与成功的GeometryCache脚本完全相同
            task = unreal.AssetImportTask()
            task.set_editor_property("automated", True)
            task.set_editor_property("filename", str(import_abc_path))
            task.set_editor_property("destination_path", uasset_folder)
            task.set_editor_property("destination_name", uasset_name)
            task.set_editor_property("replace_existing", True)
            task.set_editor_property("save", True)

            options = unreal.AbcImportSettings()
            
            # 2. --- 关键修改 ---
            options.import_type = unreal.AlembicImportType.SKELETAL
            

            # 3. 保持所有其他设置（采样、转换）与工作脚本一致
            options.sampling_settings = unreal.AbcSamplingSettings(
                sampling_type=unreal.AlembicSamplingType.PER_FRAME, 
                frame_steps=1, 
                time_steps=0.0, 
                frame_start=1, 
                frame_end=0,
                skip_empty=False
            )            
            options.conversion_settings = unreal.AbcConversionSettings(
                preset=unreal.AbcConversionPreset.CUSTOM, 
                flip_u=False, 
                flip_v=True, 
                scale=[100.0, -100.0, 100.0], 
                rotation=[90.0, 0.0, 0.0]
            )

            task.set_editor_property("options", options)

            # 使用与工作脚本完全相同的导入和保存流程
            import_tasks = [task]
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(import_tasks)
            unreal.EditorAssetLibrary.save_directory(data_root_unreal)

    return

######################################################################
# Main
######################################################################
if __name__ == "__main__":        
    unreal.log("============================================================")
    unreal.log("Running: %s" % __file__)

    current_batch = None
    num_batches = None
    if len(sys.argv) == 3:
        current_batch = int(sys.argv[1])
        num_batches = int(sys.argv[2])

    start_time = time.perf_counter()
    import_abc(data_root, data_root_unreal, current_batch, num_batches)
    print(f"SkeletalMesh batch import finished. Total import time: {(time.perf_counter() - start_time):.1f}s")