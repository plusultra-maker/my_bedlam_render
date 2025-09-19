# Copyright (c) 2023 Max Planck Society
# License: https://bedlam.is.tuebingen.mpg.de/license.html
#
# Import SMPL-X fbx files as SkeletalMesh
#

import math
from pathlib import Path
import sys
import time
import unreal

# --- Configuration ---
# Source directory containing the .fbx files
data_root = r"E:\CS\Graphics\bedlam_render\fbx"
# Target content directory in Unreal
data_root_unreal = "/Game/PS/Bedlam/SMPLX_fbx/"
# Path for the skeleton to be used. Leave as None to auto-create from the first file.
skeleton_path = None

def get_fbx_import_options(skeleton_to_use):
    """Creates and configures FBX import options."""
    options = unreal.FbxImportUI()
    # Set Skeletal Mesh options
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("import_mesh", True)
    options.skeletal_mesh_import_data.set_editor_property("import_content_type", unreal.FBXImportContentType.FBX_CONTENT_TYPE_SKELETAL_MESH)

    # Assign skeleton if one is provided
    if skeleton_to_use:
        options.set_editor_property("skeleton", skeleton_to_use)

    # Set transform options to match the original abc script
    # Scale to convert from meters (Blender) to centimeters (Unreal)
    options.skeletal_mesh_import_data.set_editor_property("import_uniform_scale", 100.0)
    # Rotate to align coordinate systems (Y-Up to Z-Up)
    options.skeletal_mesh_import_data.set_editor_property("import_rotation", unreal.Rotator(0, 0, 0))
    
    # Disable material and texture import to avoid clutter
    options.set_editor_property("import_materials", False)
    options.set_editor_property("import_textures", False)
    
    # Animation import settings
    options.set_editor_property("import_animations", True)
    options.anim_sequence_import_data.set_editor_property("import_translation", unreal.Vector(0.0, 0.0, 0.0))
    options.anim_sequence_import_data.set_editor_property("import_rotation", unreal.Rotator(0.0, 0.0, 0.0))
    options.anim_sequence_import_data.set_editor_property("import_uniform_scale", 1.0)
    
    return options

def import_fbx(data_root, data_root_unreal, current_batch, num_batches, whitelist_subjects=None, whitelist_animations=None):
    """Batch imports FBX files as Skeletal Meshes."""
    global skeleton_path
    
    # Build import list
    import_fbx_paths = sorted(Path(data_root).rglob("*.fbx"))

    if not import_fbx_paths:
        unreal.log_error(f"No .fbx files found in {data_root}")
        return

    if current_batch is not None and num_batches is not None:
        section_length = math.ceil(len(import_fbx_paths) / num_batches)
        start_index = current_batch * section_length
        end_index = min(start_index + section_length, len(import_fbx_paths))
        print(f"Processing section: {current_batch}, total sections: {num_batches}, range: [{start_index}:{end_index}]")
        import_fbx_paths = import_fbx_paths[start_index:end_index]

    # Try to load the specified skeleton
    skeleton_to_use = None
    if skeleton_path:
        skeleton_to_use = unreal.load_asset(skeleton_path)
        if not skeleton_to_use:
            unreal.log_warning(f"Could not load specified skeleton: {skeleton_path}. A new one will be created.")

    for fbx_path in import_fbx_paths:
        unreal.log(f"Processing FBX: {fbx_path}")

        uasset_folder_name = fbx_path.parent.name
        uasset_folder = f"{data_root_unreal}{uasset_folder_name}"
        uasset_name = fbx_path.stem
        uasset_path = f"{uasset_folder}/{uasset_name}"

        if unreal.EditorAssetLibrary.does_asset_exist(uasset_path):
            unreal.log(f"  Skipping import. Asset already exists: {uasset_path}")
            continue

        unreal.log(f"  Importing to: {uasset_path}")

        task = unreal.AssetImportTask()
        task.set_editor_property("automated", True)
        task.set_editor_property("filename", str(fbx_path))
        task.set_editor_property("destination_path", uasset_folder)
        task.set_editor_property("destination_name", uasset_name)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("save", True)

        # Get import options, providing the skeleton if we have one
        task.set_editor_property("options", get_fbx_import_options(skeleton_to_use))

        # Execute the import
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        
        # After the first import, if we didn't have a skeleton, find the one that was just created and use it for all subsequent imports.
        if not skeleton_to_use:
            # The skeleton is typically created with a "_Skeleton" suffix
            created_skeleton_path = f"{uasset_path}_Skeleton.{uasset_name}_Skeleton"
            skeleton_to_use = unreal.load_asset(created_skeleton_path)
            if skeleton_to_use:
                unreal.log(f"  First skeleton created and loaded: {created_skeleton_path}. This will be used for subsequent imports.")
                skeleton_path = created_skeleton_path # Save for future runs if needed
            else:
                unreal.log_error(f"  Failed to find the created skeleton at {created_skeleton_path}. Subsequent imports might create new skeletons.")
                # If we can't find it, we have to break or risk creating a skeleton for every file
                break

    unreal.EditorAssetLibrary.save_directory(data_root_unreal)
    return

######################################################################
# Main
######################################################################
if __name__ == "__main__":
    unreal.log("============================================================")
    unreal.log(f"Running: {__file__}")

    current_batch = None
    num_batches = None
    if len(sys.argv) == 3:
        current_batch = int(sys.argv[1])
        num_batches = int(sys.argv[2])

    start_time = time.perf_counter()
    import_fbx(data_root, data_root_unreal, current_batch, num_batches)
    print(f"FBX SkeletalMesh batch import finished. Total import time: {(time.perf_counter() - start_time):.1f}s")
