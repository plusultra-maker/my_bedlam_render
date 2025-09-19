# Copyright (c) 2023 Max Planck Society
# License: https://bedlam.is.tuebingen.mpg.de/license.html
#
# Create level sequences for specified animations in be_seq.csv file
#
# Required plugins: Python Editor Script Plugin, Editor Scripting, Sequencer Scripting
#

import csv
from dataclasses import dataclass
import re
from math import radians, tan
import sys, os
import time
import unreal

# Globals
WARMUP_FRAMES = 10 # Needed for proper temporal sampling on frame 0 of animations and raytracing warmup. These frames are rendered out with negative numbers and will be deleted in post render pipeline.
data_root_unreal = "/Engine/PS/Bedlam/"
clothing_actor_class_path = data_root_unreal + "Core/Materials/BE_ClothingOverlayActor.BE_ClothingOverlayActor_C"
body_root = data_root_unreal + "SMPLX_Skeletal/"
geometry_cache_body_root = data_root_unreal + "SMPLX/" 
hair_root = data_root_unreal + "Hair/CC/Meshes/"
animation_root = data_root_unreal + "SMPLX_batch01_hand_animations/"
hdri_root = data_root_unreal + "HDRI/4k/"
#hdri_suffix = "_8k"
hdri_suffix = ""

material_body_root = "/Engine/PS/Meshcapade/SMPL/Materials"
material_clothing_root = data_root_unreal + "Clothing/Materials"
texture_body_root = "/Engine/PS/Meshcapade/SMPL/MC_texture_skintones"
texture_clothing_overlay_root = data_root_unreal + "Clothing/MaterialsSMPLX/Textures"

material_hidden_name = data_root_unreal + "Core/Materials/M_SMPLX_Hidden"

bedlam_root = "/Game/Bedlam/"
level_sequence_hdri_template = bedlam_root + "LS_Template_HDRI"
level_sequences_root = bedlam_root + "LevelSequences/"
camera_root = bedlam_root + "CameraMovement/"
csv_path = r"C:\bedlam\images\test\be_seq.csv"

################################################################################

@dataclass
class SequenceBody:
    subject: str
    body_path: str
    clothing_path: str
    hair_path: str
    animation_path: str
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    roll: float
    start_frame: int
    texture_body: str
    texture_clothing: str
    texture_clothing_overlay: str

@dataclass
class CameraPose:
    x: float
    y: float
    z: float
    yaw: float
    pitch: float
    roll: float

################################################################################
def add_skeletal_mesh_for_pov(level_sequence, sequence_body_index, start_frame, end_frame, skeletal_mesh_path, skeletal_animation_path, x, y, z, yaw, pitch, roll):
    """
    为POV相机添加隐藏的SkeletalMesh用于骨骼绑定
    """
    # 调试：打印路径并检查资产是否存在
    skeletal_mesh_asset_path = skeletal_mesh_path.split("'")[1]
    animation_asset_path = skeletal_animation_path.split("'")[1]
    
    unreal.log(f"DEBUG: Trying to load skeletal mesh: {skeletal_mesh_asset_path}")
    unreal.log(f"DEBUG: Asset exists? {unreal.EditorAssetLibrary.does_asset_exist(skeletal_mesh_asset_path)}")
    
    unreal.log(f"DEBUG: Trying to load animation: {animation_asset_path}")
    unreal.log(f"DEBUG: Asset exists? {unreal.EditorAssetLibrary.does_asset_exist(animation_asset_path)}")
    
    # 调试：列出目录中的所有资产
    import_dir = "/".join(skeletal_mesh_asset_path.split("/")[:-1])
    unreal.log(f"DEBUG: Assets in directory {import_dir}:")
    all_assets = unreal.EditorAssetLibrary.list_assets(import_dir)
    for asset in all_assets:
        if "skel" in asset.lower():
            unreal.log(f"  Found skeletal asset: {asset}")
    
    # 加载SkeletalMesh和Animation
    skeletal_mesh_object = unreal.load_asset(skeletal_mesh_path.split("'")[1])
    animation_object = unreal.load_asset(skeletal_animation_path.split("'")[1])
    unreal.log(f"DEBUG: SkeletalMesh loaded successfully: {skeletal_mesh_object.get_name()}")
    skeleton = skeletal_mesh_object.skeleton
    unreal.log(f"DEBUG: Skeleton loaded successfully: {skeleton.get_name()}")
    
    if skeletal_mesh_object is None or animation_object is None:
        unreal.log_error(f"Cannot load skeletal mesh or animation: {skeletal_mesh_path}, {skeletal_animation_path}")
        return None
    
    # 创建隐藏的SkeletalMeshActor
    skeletal_mesh_actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0,0,0))
    skeletal_mesh_actor.set_actor_label(f"{skeletal_mesh_object.get_name()}_POV")
    skeletal_mesh_actor.skeletal_mesh_component.set_skeletal_mesh(skeletal_mesh_object)
    
    # 设置为隐藏
    skeletal_mesh_actor.set_actor_hidden_in_game(False)  # 临时设为可见
    skeletal_mesh_actor.skeletal_mesh_component.set_visibility(True)
    
    unreal.log(f"DEBUG: Animation length: {animation_object.sequence_length} seconds")
    #unreal.log(f"DEBUG: Animation frame count: {animation_object.get_number_of_sampling_keys()}")
    
    # 添加到序列
    skeletal_binding = level_sequence.add_spawnable_from_instance(skeletal_mesh_actor)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(skeletal_mesh_actor)
    
    # 添加动画轨道
    anim_track = skeletal_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    anim_section = anim_track.add_section()
    anim_section.params.animation = animation_object
    anim_section.set_range(start_frame, end_frame)
    
    # 设置位置和旋转
    transform_track = skeletal_binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_start_frame_bounded(False)
    transform_section.set_end_frame_bounded(False)
    transform_channels = transform_section.get_channels()
    transform_channels[0].set_default(x)     # location X
    transform_channels[1].set_default(y)     # location Y
    transform_channels[2].set_default(z)     # location Z
    transform_channels[3].set_default(roll)  # roll
    transform_channels[4].set_default(pitch) # pitch
    transform_channels[5].set_default(yaw)   # yaw
    
    return skeletal_binding


def add_geometry_cache(level_sequence, sequence_body_index, layer_suffix, start_frame, end_frame, target_object, x, y, z, yaw, pitch, roll, material=None, texture_body_path=None, texture_clothing_overlay_path=None):
    """
    Add geometry cache to LevelSequence and setup material.
    If material parameter is set then GeometryCacheActor will be spawned and the material will be used.
    Otherwise a custom clothing actor (SMPLXClothingActor) will be spawned and the provided texture inputs will be used.
    """

    # Spawned GeometryCaches will generate GeometryCacheActors where ManualTick is false by default.
    # This will cause the animation to play before the animation section in the timeline and lead to temporal sampling errors
    # on the first frame of the animation section.
    # To prevent this we need to set ManualTick to true as default setting for the GeometryCacheActor.
    # 1. Spawn default GeometryCacheActor template in level
    # 2. Set default settings for GeometryCache and ManualTick on it
    # 3. Add actor as spawnable to sequence
    # 4. Destroy template actor in level
    # Note: Conversion from possessable to spawnable currently not available in Python: https://forums.unrealengine.com/t/convert-to-spawnable-with-python/509827

    if texture_clothing_overlay_path is not None:
        # Use SMPL-X clothing overlay texture, dynamic material instance will be generated in BE_ClothingOverlayActor Construction Script
        clothing_actor_class = unreal.load_class(None, clothing_actor_class_path)
        geometry_cache_actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(clothing_actor_class, unreal.Vector(0,0,0))
        geometry_cache_actor.set_editor_property("bodytexture", unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(unreal.SoftObjectPath(texture_body_path)))
        geometry_cache_actor.set_editor_property("clothingtextureoverlay", unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(unreal.SoftObjectPath(texture_clothing_overlay_path)))
    else:
        geometry_cache_actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.GeometryCacheActor, unreal.Vector(0,0,0))
        if material is not None:
            geometry_cache_actor.get_geometry_cache_component().set_material(0, material)


    geometry_cache_actor.set_actor_label(target_object.get_name())
    geometry_cache_actor.get_geometry_cache_component().set_editor_property("looping", False) # disable looping to prevent ghosting on last frame with temporal sampling
    geometry_cache_actor.get_geometry_cache_component().set_editor_property("manual_tick", True)
    geometry_cache_actor.get_geometry_cache_component().set_editor_property("geometry_cache", target_object)

    # Add actor to new layer so that we can later use layer name when generating segmentation masks names.
    # Note: We cannot use ObjectIds of type "Actor" since actors which are added via add_spawnable_from_instance() will later use their class names when generating ObjectIds of type Actor.
    layer_subsystem = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    layer_subsystem.add_actor_to_layer(geometry_cache_actor, f"be_actor_{sequence_body_index:02}_{layer_suffix}")


    body_binding = level_sequence.add_spawnable_from_instance(geometry_cache_actor)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(geometry_cache_actor) # Delete temporary template actor from level

    geometry_cache_track = body_binding.add_track(unreal.MovieSceneGeometryCacheTrack)
    geometry_cache_section = geometry_cache_track.add_section()
    geometry_cache_section.set_range(start_frame, end_frame)

    # TODO properly set Geometry Cache target in geometry_cache_section properties to have same behavior as manual setup
    #
    # Not working: geometry_cache_section.set_editor_property("GeometryCache", body_object)
    #   Exception: MovieSceneGeometryCacheTrack: Failed to find property 'GeometryCache' for attribute 'GeometryCache' on 'MovieSceneGeometryCacheTrack'
    
    transform_track = body_binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_start_frame_bounded(False)
    transform_section.set_end_frame_bounded(False)
    transform_channels = transform_section.get_channels()
    transform_channels[0].set_default(x) # location X
    transform_channels[1].set_default(y) # location Y
    transform_channels[2].set_default(z) # location Z

    transform_channels[3].set_default(roll)  # roll
    transform_channels[4].set_default(pitch) # pitch
    transform_channels[5].set_default(yaw)   # yaw

    return body_binding


def add_hair(level_sequence, sequence_body_index, layer_suffix, start_frame, end_frame, hair_path, animation_path, x, y, z, yaw, pitch, roll,):
    """
    Add hair attached to animation sequence to LevelSequence.
    """

    unreal.log(f"    Loading static hair mesh: {hair_path}")
    hair_object = unreal.load_object(None, hair_path)
    if hair_object is None:
        unreal.log_error("      Cannot load mesh")
        return False

    unreal.log(f"    Loading animation sequence: {animation_path}")
    animsequence_object = unreal.load_asset(animation_path)
    if animsequence_object is None:
        unreal.log_error("      Cannot load animation sequence")
        return False


    # SkeletalMesh'/Engine/PS/Bedlam/SMPLX_batch01_hand_animations/rp_aaron_posed_002/rp_aaron_posed_002_1038.rp_aaron_posed_002_1038'
    animation_path_name = animation_path.split("/")[-1]
    animation_path_root = animation_path.replace(animation_path_name, "")
    skeletal_mesh_path = animation_path_root + animation_path_name.replace("_Anim", "")
    unreal.log(f"    Loading skeletal mesh: {skeletal_mesh_path}")
    skeletal_mesh_object = unreal.load_asset(skeletal_mesh_path)
    if skeletal_mesh_object is None:
        unreal.log_error("      Cannot load skeletal mesh")
        return False

    skeletal_mesh_actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0,0,0))
    skeletal_mesh_actor.set_actor_label(animsequence_object.get_name())
    skeletal_mesh_actor.skeletal_mesh_component.set_skeletal_mesh(skeletal_mesh_object)

    # Set hidden material to hide the skeletal mesh
    material = unreal.EditorAssetLibrary.load_asset(f"Material'{material_hidden_name}'")
    if not material:
        unreal.log_error('Cannot load hidden material: ' + material_hidden_name)
    skeletal_mesh_actor.skeletal_mesh_component.set_material(0, material)

    hair_actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0))
    hair_actor.set_actor_label(hair_object.get_name())
    hair_actor.set_mobility(unreal.ComponentMobility.MOVABLE)

    hair_actor.static_mesh_component.set_editor_property("static_mesh", hair_object)

    # Add actor to new layer so that we can later use layer name when generating segmentation masks names.
    # Note: We cannot use ObjectIds of type "Actor" since actors which are added via add_spawnable_from_instance() will later use their class names when generating ObjectIds of type Actor.
    layer_subsystem = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    layer_subsystem.add_actor_to_layer(hair_actor, f"be_actor_{sequence_body_index:02}_{layer_suffix}")

    # Setup LevelSequence
    skeletal_mesh_actor_binding = level_sequence.add_spawnable_from_instance(skeletal_mesh_actor)
    hair_actor_binding = level_sequence.add_spawnable_from_instance(hair_actor)

    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(skeletal_mesh_actor) # Delete temporary template actor from level
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(hair_actor) # Delete temporary template actor from level

    anim_track = skeletal_mesh_actor_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    anim_section = anim_track.add_section()
    anim_section.params.animation = animsequence_object
    anim_section.set_range(start_frame, end_frame)

    transform_track = skeletal_mesh_actor_binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_start_frame_bounded(False)
    transform_section.set_end_frame_bounded(False)
    transform_channels = transform_section.get_channels()
    transform_channels[0].set_default(x) # location X
    transform_channels[1].set_default(y) # location Y
    transform_channels[2].set_default(z) # location Z
    transform_channels[3].set_default(roll)  # roll
    transform_channels[4].set_default(pitch) # pitch
    transform_channels[5].set_default(yaw)   # yaw

    # Attach hair to animation
    attach_track = hair_actor_binding.add_track(unreal.MovieScene3DAttachTrack)
    attach_section = attach_track.add_section() # MovieScene3DAttachSection

    animation_binding_id = unreal.MovieSceneObjectBindingID()
    animation_binding_id.set_editor_property("Guid", skeletal_mesh_actor_binding.get_id())

    attach_section.set_constraint_binding_id(animation_binding_id)
    attach_section.set_editor_property("attach_socket_name", "head")

    attach_section.set_range(start_frame, end_frame)

    return True

def add_transform_track(binding, camera_pose):
    transform_track = binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_start_frame_bounded(False)
    transform_section.set_end_frame_bounded(False)
    transform_channels = transform_section.get_channels()
    transform_channels[0].set_default(camera_pose.x) # location X
    transform_channels[1].set_default(camera_pose.y) # location Y
    transform_channels[2].set_default(camera_pose.z) # location Z

    transform_channels[3].set_default(camera_pose.roll) # roll
    transform_channels[4].set_default(camera_pose.pitch) # pitch
    transform_channels[5].set_default(camera_pose.yaw) # yaw
    return

def get_focal_length(cine_camera_component, camera_hfov):
    sensor_width = cine_camera_component.filmback.sensor_width
    focal_length = sensor_width / (2.0 * tan(radians(camera_hfov)/2))
    return focal_length

def add_static_camera(level_sequence, camera_actor, camera_pose, camera_hfov):
    """
    Add static camera actor and camera cut track to level sequence.
    """

    # Add camera with transform track
    camera_binding = level_sequence.add_possessable(camera_actor)
    add_transform_track(camera_binding, camera_pose)
    """
    transform_track = camera_binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section = transform_track.add_section()
    transform_section.set_start_frame_bounded(False)
    transform_section.set_end_frame_bounded(False)
    transform_channels = transform_section.get_channels()
    transform_channels[0].set_default(camera_pose.x) # location X
    transform_channels[1].set_default(camera_pose.y) # location Y
    transform_channels[2].set_default(camera_pose.z) # location Z

    transform_channels[3].set_default(camera_pose.roll) # roll
    transform_channels[4].set_default(camera_pose.pitch) # pitch
    transform_channels[5].set_default(camera_pose.yaw) # yaw
    """

    if camera_hfov is not None:
        # Add focal length CameraComponent track to match specified hfov

        # Add a cine camera component binding using the component of the camera actor
        cine_camera_component = camera_actor.get_cine_camera_component()
        camera_component_binding = level_sequence.add_possessable(cine_camera_component)
        camera_component_binding.set_parent(camera_binding)

        # Add a focal length track and default it to 60
        focal_length_track = camera_component_binding.add_track(unreal.MovieSceneFloatTrack)
        focal_length_track.set_property_name_and_path('CurrentFocalLength', 'CurrentFocalLength')
        focal_length_section = focal_length_track.add_section()
        focal_length_section.set_start_frame_bounded(False)
        focal_length_section.set_end_frame_bounded(False)

        focal_length = get_focal_length(cine_camera_component, camera_hfov)
        focal_length_section.get_channels()[0].set_default(focal_length)

    camera_cut_track = level_sequence.add_master_track(unreal.MovieSceneCameraCutTrack)
    camera_cut_section = camera_cut_track.add_section()
    camera_cut_section.set_start_frame(-WARMUP_FRAMES) # Use negative frames as warmup frames
    camera_binding_id = unreal.MovieSceneObjectBindingID()
    camera_binding_id.set_editor_property("Guid", camera_binding.get_id())
    camera_cut_section.set_editor_property("CameraBindingID", camera_binding_id)

    return camera_cut_section

def change_binding_end_keyframe_times(binding, new_frame):
    for track in binding.get_tracks():
        for section in track.get_sections():
            for channel in section.get_channels():
                channel_keys = channel.get_keys()
                if len(channel_keys) > 0:
                    if len(channel_keys) != 2: # only change end keyframe time if channel has two keyframes
                        unreal.log_error("WARNING: Channel does not have two keyframes. Not changing last keyframe to sequence end frame.")
                    else:
                        end_key = channel_keys[1]
                        end_key.set_time(unreal.FrameNumber(new_frame))

def add_level_sequence(name, camera_actor, camera_pose, ground_truth_logger_actor, sequence_bodies, sequence_frames, hdri_name, camera_hfov=None, camera_movement="Static", cameraroot_yaw=None, cameraroot_location=None, pov_camera=False):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    level_sequence_path = level_sequences_root + name

    # Check for existing LevelSequence and delete it to avoid message dialog when creating asset which exists
    if unreal.EditorAssetLibrary.does_asset_exist(level_sequence_path):
        unreal.log("  Deleting existing old LevelSequence: " + level_sequence_path)
        unreal.EditorAssetLibrary.delete_asset(level_sequence_path)

    # Generate LevelSequence, either via template (HDRI, camera movement) or from scratch
    if hdri_name is not None:
        # Duplicate template HDRI LevelSequence
        if not unreal.EditorAssetLibrary.does_asset_exist(level_sequence_hdri_template):
            unreal.log_error("Cannot find LevelSequence HDRI template: " + level_sequence_hdri_template)
            return False
        level_sequence = unreal.EditorAssetLibrary.duplicate_asset(level_sequence_hdri_template, level_sequence_path)
        hdri_path = f"{hdri_root}{hdri_name}{hdri_suffix}"
        unreal.log(f"  Loading HDRI: {hdri_path}")
        hdri_object = unreal.load_object(None, hdri_path)
        if hdri_object is None:
            unreal.log_error("Cannot load HDRI")
            return False

        # Set loaded HDRI as Skylight cubemap in sequencer
        for binding in level_sequence.get_possessables():
            binding_name = binding.get_name()
            if (binding_name == "Skylight"):
                for track in binding.get_tracks():
                    for section in track.get_sections():
                        for channel in section.get_channels():
                            channel.set_default(hdri_object)
    elif camera_movement != "Static":
        # Duplicate template camera LevelSequence
        level_sequence_camera_template = f"{camera_root}LS_Camera_{camera_movement}"
        if not unreal.EditorAssetLibrary.does_asset_exist(level_sequence_camera_template):
            unreal.log_error("Cannot find LevelSequence camera template: " + level_sequence_camera_template)
            return False
        level_sequence = unreal.EditorAssetLibrary.duplicate_asset(level_sequence_camera_template, level_sequence_path)
    else:
        level_sequence = unreal.AssetTools.create_asset(asset_tools, asset_name = name, package_path = level_sequences_root, asset_class = unreal.LevelSequence, factory = unreal.LevelSequenceFactoryNew())

    # Set frame rate to 30fps
    frame_rate = unreal.FrameRate(numerator = 30, denominator = 1)
    level_sequence.set_display_rate(frame_rate)

    cameraroot_binding = None
    camera_cut_section = None

    if not pov_camera:
        if camera_movement == "Static":
            # Create new camera
            camera_cut_section = add_static_camera(level_sequence, camera_actor, camera_pose, camera_hfov)
        else:
            # Use existing camera from LevelSequence template
            master_track = level_sequence.get_master_tracks()[0]
            camera_cut_section = master_track.get_sections()[0]
            camera_cut_section.set_start_frame(-WARMUP_FRAMES) # Use negative frames as warmup frames

            if camera_movement.startswith("Zoom") or camera_movement.startswith("Orbit"):
                # Add camera transform track and set static camera pose
                for binding in level_sequence.get_possessables():
                    binding_name = binding.get_name()
                    if binding_name == "BE_CineCameraActor_Blueprint":
                        add_transform_track(binding, camera_pose)

                    if binding_name == "CameraComponent":
                        # Set HFOV
                        focal_length = get_focal_length(camera_actor.get_cine_camera_component(), camera_hfov)
                        binding.get_tracks()[0].get_sections()[0].get_channels()[0].set_default(focal_length)

                    if camera_movement.startswith("Zoom"):
                        if binding_name == "CameraComponent":
                            # Set end focal length keyframe time to end of sequence
                            change_binding_end_keyframe_times(binding, sequence_frames)
                    elif camera_movement.startswith("Orbit"):
                        if binding_name == "BE_CameraRoot":
                            cameraroot_binding = binding
                            change_binding_end_keyframe_times(binding, sequence_frames)
    else:
        # --- new pov logic ---
        unreal.log(f"  Setting up POV camera for sequence {name}")
        camera_cut_track = level_sequence.add_master_track(unreal.MovieSceneCameraCutTrack)
        camera_cut_section = camera_cut_track.add_section()
        camera_cut_section.set_start_frame(-WARMUP_FRAMES)

    if (cameraroot_yaw is not None) or (cameraroot_location is not None):
        cameraroot_actor = camera_actor.get_attach_parent_actor()
        if cameraroot_actor is None:
            unreal.log_error("Cannot find camera root actor for CineCameraActor")
            return False

        transform_channels = None
        if cameraroot_binding is None:
            # Add camera root actor to level sequence
            cameraroot_binding = level_sequence.add_possessable(cameraroot_actor)
            transform_track = cameraroot_binding.add_track(unreal.MovieScene3DTransformTrack)
            transform_section = transform_track.add_section()
            transform_section.set_start_frame_bounded(False)
            transform_section.set_end_frame_bounded(False)
            transform_channels = transform_section.get_channels()
            if (cameraroot_yaw is not None):
                transform_channels[5].set_default(cameraroot_yaw) # yaw
            else:
                transform_channels[5].set_default(0.0)
        else:
            if cameraroot_yaw is not None:
                # Add cameraroot to existing keyframed yaw values
                transform_channels = cameraroot_binding.get_tracks()[0].get_sections()[0].get_channels()
                yaw_channel = transform_channels[5]
                channel_keys = yaw_channel.get_keys()
                for key in channel_keys:
                    key.set_value(key.get_value() + cameraroot_yaw)

        if cameraroot_location is None:
            cameraroot_location = cameraroot_actor.get_actor_location() # Default camera root location is not automatically taken from level actor when adding track via Python

        transform_channels[0].set_default(cameraroot_location.x)
        transform_channels[1].set_default(cameraroot_location.y)
        transform_channels[2].set_default(cameraroot_location.z)

    end_frame = sequence_frames
    if camera_cut_section:
        camera_cut_section.set_end_frame(end_frame)
    level_sequence.set_playback_start(-WARMUP_FRAMES) # Use negative frames as warmup frames
    level_sequence.set_playback_end(end_frame)

    # Add ground truth logger if available and keyframe sequencer frame numbers into Frame variable
    if ground_truth_logger_actor is not None:
        logger_binding = level_sequence.add_possessable(ground_truth_logger_actor)

        frame_track = logger_binding.add_track(unreal.MovieSceneIntegerTrack)
        frame_track.set_property_name_and_path('Frame', 'Frame')
        frame_track_section = frame_track.add_section()
        frame_track_section.set_range(-WARMUP_FRAMES, end_frame)
        frame_track_channel = frame_track_section.get_channels()[0]
        if WARMUP_FRAMES > 0:
            frame_track_channel.add_key(time=unreal.FrameNumber(-WARMUP_FRAMES), new_value=-1)

        for frame_number in range (0, end_frame):
            frame_track_channel.add_key(time=unreal.FrameNumber(frame_number), new_value=frame_number)

        # Add level sequence name
        sequence_name_track = logger_binding.add_track(unreal.MovieSceneStringTrack)
        sequence_name_track.set_property_name_and_path('SequenceName', 'SequenceName')
        sequence_name_section = sequence_name_track.add_section()
        sequence_name_section.set_start_frame_bounded(False)
        sequence_name_section.set_end_frame_bounded(False)

        sequence_name_section.get_channels()[0].set_default(name)

    pov_host_binding = None
    pov_skeletal_binding = None  

    for sequence_body_index, sequence_body in enumerate(sequence_bodies):

        body_object = unreal.load_object(None, sequence_body.body_path)
        if body_object is None:
            unreal.log_error(f"Cannot load body asset: {sequence_body.body_path}")
            return False

        animation_start_frame = -sequence_body.start_frame
        animation_end_frame = sequence_frames

        # Check if we use clothing overlay textures instead of textured clothing geometry
        if sequence_body.texture_clothing_overlay is not None:

            if sequence_body.texture_body.startswith("skin_f"):
                gender = "female"
            else:
                gender = "male"

            # Set Soft Object Paths to textures
            texture_body_path = f"Texture2D'{texture_body_root}/{gender}/skin/{sequence_body.texture_body}.{sequence_body.texture_body}'"
            texture_clothing_overlay_path = f"Texture2D'{texture_clothing_overlay_root}/{sequence_body.texture_clothing_overlay}.{sequence_body.texture_clothing_overlay}'"

            body_binding=add_geometry_cache(level_sequence, sequence_body_index, "body", animation_start_frame, animation_end_frame, body_object, sequence_body.x, sequence_body.y, sequence_body.z, sequence_body.yaw, sequence_body.pitch, sequence_body.roll, None, texture_body_path, texture_clothing_overlay_path)

            if pov_camera and sequence_body_index == 0:
                pov_host_binding = body_binding
    
                if hasattr(sequence_body, 'skeletal_mesh_path') and sequence_body.skeletal_mesh_path:
                    pov_skeletal_binding = add_skeletal_mesh_for_pov(
                        level_sequence, 
                        sequence_body_index, 
                        animation_start_frame, 
                        animation_end_frame, 
                        sequence_body.skeletal_mesh_path,
                        sequence_body.skeletal_animation_path,
                        sequence_body.x, sequence_body.y, sequence_body.z, 
                        sequence_body.yaw, sequence_body.pitch, sequence_body.roll
                    )
                    
                    visibility_track = body_binding.add_track(unreal.MovieSceneVisibilityTrack)
                    visibility_section = visibility_track.add_section()
                    visibility_section.set_range(-WARMUP_FRAMES, end_frame)
                    visibility_section.get_channels()[0].set_default(False)
                else:
                    unreal.log_warning("POV mode enabled but skeletal mesh paths not available")

        else:
            # Add body
            material = None
            if sequence_body.texture_body is not None:
                material_asset_path = f"{material_body_root}/MI_{sequence_body.texture_body}"
                material = unreal.EditorAssetLibrary.load_asset(f"MaterialInstanceConstant'{material_asset_path}'")
                if not material:
                    unreal.log_error(f"Cannot load material: {material_asset_path}")
                    return False

            body_binding=add_geometry_cache(level_sequence, sequence_body_index, "body", animation_start_frame, animation_end_frame, body_object, sequence_body.x, sequence_body.y, sequence_body.z, sequence_body.yaw, sequence_body.pitch, sequence_body.roll, material)


            if pov_camera and sequence_body_index == 0:
                pov_host_binding = body_binding
    
                if hasattr(sequence_body, 'skeletal_mesh_path') and sequence_body.skeletal_mesh_path:
                    pov_skeletal_binding = add_skeletal_mesh_for_pov(
                        level_sequence, 
                        sequence_body_index, 
                        animation_start_frame, 
                        animation_end_frame, 
                        sequence_body.skeletal_mesh_path,
                        sequence_body.skeletal_animation_path,
                        sequence_body.x, sequence_body.y, sequence_body.z, 
                        sequence_body.yaw, sequence_body.pitch, sequence_body.roll
                    )
                    
                    visibility_track = body_binding.add_track(unreal.MovieSceneVisibilityTrack)
                    visibility_section = visibility_track.add_section()
                    visibility_section.set_range(-WARMUP_FRAMES, end_frame)
                    visibility_section.get_channels()[0].set_default(False)
                else:
                    unreal.log_warning("POV mode enabled but skeletal mesh paths not available")
                
            
            # Add clothing if available
            if sequence_body.clothing_path is not None:
                clothing_object = unreal.load_object(None, sequence_body.clothing_path)
                if clothing_object is None:
                    unreal.log_error(f"Cannot load clothing asset: {sequence_body.clothing_path}")
                    return False

                material = None
                if sequence_body.texture_clothing is not None:
                    material_asset_path = f"{material_clothing_root}/{sequence_body.subject}/MI_{sequence_body.subject}_{sequence_body.texture_clothing}"
                    material = unreal.EditorAssetLibrary.load_asset(f"MaterialInstanceConstant'{material_asset_path}'")
                    if not material:
                        unreal.log_error(f"Cannot load material: {material_asset_path}")
                        return False

                add_geometry_cache(level_sequence, sequence_body_index, "clothing", animation_start_frame, animation_end_frame, clothing_object, sequence_body.x, sequence_body.y, sequence_body.z, sequence_body.yaw, sequence_body.pitch, sequence_body.roll, material)

        # Add hair
        if sequence_body.hair_path is not None:
            success = add_hair(level_sequence, sequence_body_index, "hair", animation_start_frame, animation_end_frame, sequence_body.hair_path, sequence_body.animation_path, sequence_body.x, sequence_body.y, sequence_body.z, sequence_body.yaw, sequence_body.pitch, sequence_body.roll)
            if not success:
                return False
            
    if pov_host_binding is not None:
        # 关键改动：将相机创建为Spawnable，而不是使用Possessable
        camera_binding = level_sequence.add_spawnable_from_class(unreal.CineCameraActor)
        camera_binding.set_name("POVCineCamera")
        
        # 设置POV相机的HFOV
        if camera_hfov is not None:
            focal_length_track = camera_binding.add_track(unreal.MovieSceneFloatTrack)
            focal_length_track.set_property_name_and_path('CineCameraComponent.CurrentFocalLength', 'CineCameraComponent.CurrentFocalLength')
            focal_length_section = focal_length_track.add_section()
            focal_length_section.set_start_frame_bounded(False)
            focal_length_section.set_end_frame_bounded(False)

            source_cine_component = camera_actor.get_cine_camera_component()
            if source_cine_component:
                focal_length = get_focal_length(source_cine_component, camera_hfov)
                focal_length_section.get_channels()[0].set_default(focal_length)
            else:
                unreal.log_warning("Could not get CineCameraComponent from source camera actor to calculate focal length. HFOV will not be set.")

        if pov_skeletal_binding:
            # 添加附加轨道，这是定位的核心
            attach_track = camera_binding.add_track(unreal.MovieScene3DAttachTrack)
            attach_section = attach_track.add_section()
            
            # 关键修复：先设置绑定ID，再设置范围（与hair函数保持一致）
            skeletal_binding_id = unreal.MovieSceneObjectBindingID()
            skeletal_binding_id.set_editor_property("Guid", pov_skeletal_binding.get_id())
            
            attach_section.set_constraint_binding_id(skeletal_binding_id)
            attach_section.set_editor_property("attach_socket_name", "head")
            
            # 最后设置范围
            attach_section.set_range(-WARMUP_FRAMES, end_frame)
            
            unreal.log(f"  POV camera attached to 'head' bone on SkeletalMesh")
            # 关键修复：设置附加偏移，而不是使用Transform轨道
            # 这样可以避免Transform轨道覆盖Attach效果
            pov_offset_location = unreal.Vector(15.0, 0.0, 10.0)  # X向前, Y向右, Z向上
            pov_offset_rotation = unreal.Rotator(0.0, 0.0, 0.0)   # Roll, Pitch, Yaw
            
            #attach_section.set_editor_property("attach_location", pov_offset_location)
            #attach_section.set_editor_property("attach_rotation", pov_offset_rotation)
            
            #unreal.log(f"  POV camera attached to 'head' bone with offset {pov_offset_location}")
            
            # 移除Transform轨道 - 这是关键修复！
            # 不再添加Transform轨道，避免与Attach轨道冲突

        # 将Camera Cut轨道的相机设置为我们刚绑定的Spawnable相机
        camera_binding_id = unreal.MovieSceneObjectBindingID()
        camera_binding_id.set_editor_property("Guid", camera_binding.get_id())
        camera_cut_section.set_editor_property("CameraBindingID", camera_binding_id)
        
    unreal.EditorAssetLibrary.save_asset(level_sequence.get_path_name())

    return True

######################################################################
# Main
######################################################################
if __name__ == '__main__':        
    unreal.log("============================================================")
    unreal.log("Running: %s" % __file__)

    if len(sys.argv) >= 2:
        csv_path = sys.argv[1]

    camera_movement = "Static"
    if len(sys.argv) >= 3:
        camera_movement = sys.argv[2]

    start_time = time.perf_counter()

    # Find CineCameraActor and BE_GroundTruthLogger in current map
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() # deprecated: unreal.EditorLevelLibrary.get_all_level_actors()
    camera_actor = None
    ground_truth_logger_actor = None
    for actor in actors:
        if actor.static_class() == unreal.CineCameraActor.static_class():
            camera_actor = actor
        elif actor.get_class().get_name() == "BE_GroundTruthLogger_C":
            ground_truth_logger_actor = actor

    success = True

    if camera_actor is None:
        unreal.log_error("Cannot find CineCameraActor in current map")
        success = False
    else:
        # Generate LevelSequences for defined sequences in csv file
        csv_reader = None
        with open(csv_path, mode="r") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            csv_rows = list(csv_reader) # Convert to list of rows so that we can look ahead, this will skip header
            sequence_bodies = []

            sequence_name = None
            sequence_frames = 0
            hdri_name = None
            camera_hfov = None
            camera_pose = None
            cameraroot_yaw = None
            cameraroot_location = None
            pov_camera = False

            for row_index, row in enumerate(csv_rows):
                if row["Type"] == "Comment":
                    continue

                if row["Type"] == "Group":
                    camera_pose = CameraPose(float(row["X"]), float(row["Y"]), float(row["Z"]), float(row["Yaw"]), float(row["Pitch"]), float(row["Roll"]))

                    # Parse additional group configuration
                    values = row["Comment"].split(";")
                    dict_keys = []
                    dict_values = []
                    for value in values:
                        dict_keys.append(value.split("=")[0])
                        dict_values.append(value.split("=")[1])
                    group_config = dict(zip(dict_keys, dict_values))
                    sequence_name = group_config["sequence_name"]
                    sequence_frames = int(group_config["frames"])

                    # Check if HDRI was specified
                    if "hdri" in group_config:
                        hdri_name = group_config["hdri"]
                    else:
                        hdri_name = None

                    # Check if camera HFOV was specified
                    if "camera_hfov" in group_config:
                        camera_hfov = float(group_config["camera_hfov"])
                    else:
                        camera_hfov = None

                    # check if is POV camera
                    if "pov_camera" in group_config and group_config["pov_camera"] == "true":
                        pov_camera = True
                    else:
                        pov_camera = False

                    if "cameraroot_yaw" in group_config:
                        cameraroot_yaw = float(group_config["cameraroot_yaw"])
                    else:
                        cameraroot_yaw = None

                    if "cameraroot_x" in group_config:
                        cameraroot_x =float(group_config["cameraroot_x"])
                        cameraroot_y =float(group_config["cameraroot_y"])
                        cameraroot_z =float(group_config["cameraroot_z"])
                        cameraroot_location = unreal.Vector(cameraroot_x, cameraroot_y, cameraroot_z)

                    unreal.log(f"  Generating level sequence: {sequence_name}, frames={sequence_frames}, hdri={hdri_name}, camera_hfov={camera_hfov}")
                    sequence_bodies = []

                    continue

                if row["Type"] == "Body":
                    index = int(row["Index"])
                    body = row["Body"]


                    x = float(row["X"])
                    y = float(row["Y"])
                    z = float(row["Z"])
                    yaw = float(row["Yaw"])
                    pitch = float(row["Pitch"])
                    roll = float(row["Roll"])

                    # Parse additional body configuration
                    values = row["Comment"].split(";")
                    dict_keys = []
                    dict_values = []
                    for value in values:
                        dict_keys.append(value.split("=")[0])
                        dict_values.append(value.split("=")[1])
                    body_config = dict(zip(dict_keys, dict_values))
                    start_frame = 0
                    if "start_frame" in body_config:
                        start_frame = int(body_config["start_frame"])

                    texture_body = None
                    if "texture_body" in body_config:
                        texture_body = body_config["texture_body"]

                    texture_clothing = None
                    if "texture_clothing" in body_config:
                        texture_clothing = body_config["texture_clothing"]

                    texture_clothing_overlay = None
                    if "texture_clothing_overlay" in body_config:
                        texture_clothing_overlay = body_config["texture_clothing_overlay"]

                    hair_path = None
                    if "hair" in body_config:
                        if not level_sequence_hdri_template.endswith("_Hair"):
                            level_sequence_hdri_template += "_Hair"

                        hair_type = body_config["hair"]
                        # StaticMesh'/Engine/PS/Bedlam/Hair/CC/Meshes/SMPLX_M_Hair_Center_part_curtains/SMPLX_M_Hair_Center_part_curtains.SMPLX_M_Hair_Center_part_curtains'
                        hair_path = f"StaticMesh'{hair_root}{hair_type}/{hair_type}.{hair_type}'"

                    match = re.search(r"(.+)_(.+)", body)
                    if not match:
                        unreal.log_error(f"Invalid body name pattern: {body}")
                        success = False
                        break

                    subject = match.group(1)
                    animation_id = match.group(2)

                    # Body: GeometryCache'/Engine/PS/Bedlam/SMPLX/rp_aaron_posed_002/rp_aaron_posed_002_0000.rp_aaron_posed_002_0000'
                    # Clothing: GeometryCache'/Engine/PS/Bedlam/Clothing/rp_aaron_posed_002/rp_aaron_posed_002_0000_clo.rp_aaron_posed_002_0000_clo'

                    if pov_camera:
                        # POV模式：加载SkeletalMesh和Animation
                        unreal.log("    POV mode enabled, using SkeletalMesh and Animation")
                        skeletal_mesh_path = f"SkeletalMesh'{body_root}{subject}/{body}.{body}'"
                        skeletal_animation_path = f"AnimSequence'{body_root}{subject}/{body}.{body}_Animation'"
                        # 同时也需要GeometryCache用于渲染
                        body_path = f"GeometryCache'{geometry_cache_body_root}{subject}/{body}.{body}'"
                    else:
                        # 非POV模式：只使用GeometryCache
                        body_path = f"GeometryCache'{geometry_cache_body_root}{subject}/{body}.{body}'"
                        skeletal_mesh_path = None
                        skeletal_animation_path = None

                    have_body = unreal.EditorAssetLibrary.does_asset_exist(body_path)
                    if not have_body:
                        unreal.log_error("No asset found for body path: " + body_path)
                        success = False
                        break

                    unreal.log("    Processing body: " + body_path)

                    clothing_path = None
                    if texture_clothing is not None:
                        clothing_path = body_path.replace("SMPLX", "Clothing")
                        clothing_path = clothing_path.replace(animation_id, f"{animation_id}_clo")

                        have_clothing = unreal.EditorAssetLibrary.does_asset_exist(clothing_path)
                        if not have_clothing:
                            unreal.log_error("No asset found for clothing path: " + clothing_path)
                            success = False
                            break

                        unreal.log("    Clothing: " + clothing_path)

                    animation_path = None
                    if hair_path is not None:
                        # AnimSequence'/Engine/PS/Bedlam/SMPLX_batch01_hand_animations/rp_aaron_posed_002/rp_aaron_posed_002_1000_Anim.rp_aaron_posed_002_1000_Anim'
                        animation_path = f"AnimSequence'{animation_root}{subject}/{body}_Anim.{body}_Anim'"

                    sequence_body = SequenceBody(subject, body_path, clothing_path, hair_path, animation_path, x, y, z, yaw, pitch, roll, start_frame, texture_body, texture_clothing, texture_clothing_overlay)
                    
                    if pov_camera:
                        sequence_body.skeletal_mesh_path = skeletal_mesh_path
                        sequence_body.skeletal_animation_path = skeletal_animation_path
                    else:
                        sequence_body.skeletal_mesh_path = None
                        sequence_body.skeletal_animation_path = None
                    
                    sequence_bodies.append(sequence_body)

                    # Check if body was last item in current sequence
                    add_sequence = False
                    if index >= (len(csv_rows) - 1):
                        add_sequence = True
                    elif csv_rows[row_index + 1]["Type"] != "Body":
                        add_sequence = True

                    if add_sequence:
                        success = add_level_sequence(sequence_name, camera_actor, camera_pose, ground_truth_logger_actor, sequence_bodies, sequence_frames, hdri_name, camera_hfov, camera_movement, cameraroot_yaw, cameraroot_location, pov_camera)

                        # Remove added layers used for segmentation mask naming
                        layer_subsystem = unreal.get_editor_subsystem(unreal.LayersSubsystem)
                        layer_names = layer_subsystem.add_all_layer_names_to()
                        for layer_name in layer_names:
                            if str(layer_name).startswith("be_actor"):
                                layer_subsystem.delete_layer(layer_name)

                        if not success:
                            break

    if success:
        unreal.log(f"LevelSequence generation finished. Total time: {(time.perf_counter() - start_time):.1f}s")
        sys.exit(0)
    else:
        unreal.log_error(f"LevelSequence generation failed. Total time: {(time.perf_counter() - start_time):.1f}s")
        sys.exit(1)
