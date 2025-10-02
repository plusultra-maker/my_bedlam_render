#!/usr/bin/env python
# Copyright (c) 2023 Max Planck Society
# License: https://bedlam.is.tuebingen.mpg.de/license.html
#
# Batch import SMPL-X .fbx animations as Skeletal Meshes into Unreal using multiprocessing
#
# Notes:
# + Python for Windows: py -3 import_fbx_smplx_skeleton_batch.py
#

from multiprocessing import Pool
from pathlib import Path
import subprocess
import sys
import time

# Globals
UNREAL_APP_PATH = r"H:\UE_5.0\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
UNREAL_PROJECT_PATH = r"C:\Users\maverick\Documents\Unreal Projects\Bedlam_ppl\Bedlam_ppl.uproject"
IMPORT_SCRIPT_PATH = "E:/CS/Graphics/bedlam_render/unreal/import/import_fbx_smplx_skeleton.py" # need forward slashes when calling via -ExecutePythonScript

def worker(unreal_app_path, unreal_project_path, import_script_path, batch_index, num_batches):
    # "C:\UE\UE_5.0\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\UEProjects\5.0\Sandbox5\Sandbox5.uproject" -stdout -FullStdOutLogOutput -ExecutePythonScript="C:/bedlam_render/unreal/import/import_fbx_smplx_skeleton.py 0 10"
    log_filename = f"fbx_import_log_batch_{batch_index}.log"
    
    # In Unreal 5.0, redirecting log output to a file is better handled via command line args
    subprocess_args = [
        unreal_app_path, 
        unreal_project_path, 
        "-stdout",
        "-FullStdOutLogOutput",
        f"-ExecutePythonScript={import_script_path} {batch_index} {num_batches}",
        f"-log={log_filename}"
    ]
    
    print(f"Running batch {batch_index} with args: {subprocess_args}")
    subprocess.run(subprocess_args)
    return True

def worker_args(args):
    return worker(*args)

################################################################################
# Main
################################################################################
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print('Usage: %s NUM_BATCHES PROCESSES' % (sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    num_batches = int(sys.argv[1])
    processes = int(sys.argv[2])

    print(f"Starting pool with {processes} processes, batches: {num_batches}\n", file=sys.stderr)
    pool = Pool(processes)

    start_time = time.perf_counter()
    tasklist = []    
    for batch_index in range(num_batches):
        tasklist.append( (UNREAL_APP_PATH, UNREAL_PROJECT_PATH, IMPORT_SCRIPT_PATH, batch_index, num_batches) )

    result = pool.map(worker_args, tasklist)

    print(f"Finished. Total batch conversion time: {(time.perf_counter() - start_time):.1f}s")

# python import_fbx_smplx_skeleton_batch.py 16 8