"""Galaxy on Fire 2 ship skin renderer

EARLY UNFINISHED PROTOTYPE

Written by Trimatix
"""
try:
    import bpy # type: ignore[reportMissingImports]
except ImportError:
    raise ValueError("This script can only be run by blender.")

import os
from os.path import join
from math import radians
from mathutils import *
import pathlib



##### CONFIG VARIABLES #####

# Determine the location of this script file. Used  for configuring script working paths below.
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

# The camera's view distance. 5000 Should be plenty, but for larger models you may need to raise it.
# Tested with the Vossk Battlecruiser model.
CAM_CLIP = 5000
# Working directory for the script. This is used for temporarily saving intermediate textures
# e.g between mask applications (TODO: Save the completed texture to a cache directory [the bbShipSkin dir])
RENDER_TEMP_DIR = join(SCRIPT_PATH, "temp")
# Path to the script's render variables file.
# Line 1:   Path to the model to render
# Line 2:   If rendering a single texture, the path to that texture.
#           If rendering a base texture on top of another image, the path to the base texture.
# Line 3:   The path to the under-layer image if using one; the image to place underneith the base texture
# Line 4:   The path to the secondary texture region image if using one;
#           This will be composited with respect to the secondary_mask.jpg found in the same directory as the model.
#           This mask MUST exist in order for a passed secondary texture region image to be used.
# Line 4:   The path to the tertiary texture region image if using one;
#           This will be composited with respect to the tertiary_mask.jpg found in the same directory as the model.
#           This mask MUST exist in order for a passed tertiary texture region image to be used.
RENDER_ARGS_PATH = join(SCRIPT_PATH, "render_vars")

print(f"SCRIPT_PATH: {SCRIPT_PATH}")
print(f"RENDER_TEMP_DIR: {RENDER_TEMP_DIR}")
print(f"RENDER_ARGS_PATH: {RENDER_ARGS_PATH}")

if not os.path.isdir(RENDER_TEMP_DIR):
    os.makedirs(RENDER_TEMP_DIR)

argsDir = os.path.dirname(RENDER_TEMP_DIR) if RENDER_TEMP_DIR else ""
if not os.path.isdir(argsDir):
    os.makedirs(argsDir)


##### UTIL OBJECTS #####

class RenderArgs:
    """A data class representing arguments passed to the renderer.

    :var model_fullpath: The path to the model to render
    :vartype model_fullpath: str
    :var model_dir: Path to the directory containing the model
    :vartype model_dir: str
    :var model_filename: The name and file extension of the model file
    :vartype model_filename: str
    :var model_filename_noext: The name of the model file with no extension
    :vartype model_filename_noext: str
    :var texture_path: path to the texture file to render on the model
    :vartype texture_path: str
    :var material: path to the material to render. It must be in model_dir, and called model_filename_noext + '.mtl'
    :vartype material: str
    """

    def __init__(self, res_x: int, res_y: int, output_file_path: str, model_path: str, texture_path: str,
            numSamples: int):
        """
        :param int res_x: The width in pixels of the render resolution.
        :param int res_y: The height in pixels of the render resolution.
        :param str output_file_path: The path to render the output image to, including the file name and extension
        :param str model_path: The path to the model to render
        :param str texture_path: path to the texture file to render on the model
        :param int numSamples: The number of samples to render per pixel
        """
        self.res_x = res_x
        self.res_y = res_y
        self.output_file_path = output_file_path
        self.model_fullpath = model_path
        self.texture_path = texture_path
        #self.model_dir = str(Path(self.model_fullpath).parent)
        #self.model_filename = Path(self.model_fullpath).name
        #self.model_filename_noext = Path(self.model_fullpath).stem
        self.material = self._find_mtl_file()
        #self.material = str(Path(self.model_fullpath).with_suffix(".mtl"))
        self.numSamples = numSamples

    def _find_mtl_file(self) -> str:
        """Dynamically find the MTL file using multiple strategies."""
        obj_dir = os.path.dirname(self.model_fullpath)
        obj_basename = os.path.splitext(os.path.basename(self.model_fullpath))[0]

        print(f"Looking for MTL file for: {self.model_fullpath}")
        print(f"OBJ directory: {obj_dir}")
        print(f"OBJ basename: {obj_basename}")

        # Look for MTL with same basename as OBJ
        same_name_mtl = os.path.join(obj_dir, f"{obj_basename}.mtl")
        if os.path.exists(same_name_mtl):
            print(f"✓ Found MTL with matching basename: {same_name_mtl}")
            return os.path.abspath(same_name_mtl)

        # Fallback to original hardcoded behavior
        fallback_mtl = os.path.join(obj_dir, "material.mtl")
        print(f"⚠ No MTL files found, using fallback: {fallback_mtl}")
        return os.path.abspath(fallback_mtl)

def getRenderArgs() -> RenderArgs:
    """Parse the arguments passed to the script via RENDER_ARGS_PATH, and return them in a RenderArgs object.

    :return: A RenderArgs object containing the passed renderer arguments
    :rtype: RenderArgs
    """
    args = []
    with open(RENDER_ARGS_PATH, "r") as f:
        for line in f.readlines():
            args.append(line.rstrip("\n"))
        print(f"Raw args: {args}")
    return RenderArgs(int(args[0].split("x")[0]), int(args[0].split("x")[1]), args[1], args[2], args[3], int(args[4]))



##### LOAD RENDERER ARGUMENTS #####

# Fetch renderer arguments
args = getRenderArgs()

print(f"args.model_fullpath: {args.model_fullpath}")
print(f"args.output_file_path: {args.output_file_path}")
print(f"args.texture_path: {args.texture_path}")
print(f"args.material: {args.material}")

##### CONFIGURE THE SCENE #####

# Point the material at the requested texture
#
# Temp hack as map_Kd is evaluated as relative to the model folder...
# Since we're resolving absolute paths, a relative path can be calculated by
# working back to the root with `../` and appending the texture's
# absolute path.  Currently that is 8 directorys we'd need to back out of,
# so hard-coding that in for now.  Better would be to calculate that based
# on the model directory and generate it programmatically...
# ../../../../../../../../
with open(args.material, "a") as f:
    # f.write("map_Kd " + rel_texture_path)
    f.write("map_Kd ../../../../../../../.." + args.texture_path)

ctx = bpy.context
# import the model into blender's scene
bpy.ops.wm.obj_import(filepath=args.model_fullpath, forward_axis='NEGATIVE_Z', up_axis='Y', filter_glob="*.obj;*.mtl")

# ensure nothing is currently selected, in case the camera is selected for some reason
bpy.ops.object.select_all(action='DESELECT')

# find the imported model in the scene
for obj in ctx.visible_objects:
    # Theoretically, nothing should be in the scene except for the model and the camera
    if obj.type != 'CAMERA':
        # Select the model
        obj.select_set(True)
        # Point the model in the correct direction
        obj.rotation_euler[0] = radians(0)
        # Set the camera view distance as configured earlier
        ctx.scene.camera.data.clip_end = CAM_CLIP



##### RENDER THE MODEL #####

# Set render resolution
ctx.scene.render.resolution_x = args.res_x
ctx.scene.render.resolution_y = args.res_y
ctx.scene.render.resolution_percentage = 100
bpy.context.scene.cycles.samples = args.numSamples
# Set the renderer (eevee renders some strange perspective stuff...?)
ctx.scene.render.engine = 'CYCLES'
# Set the render output file
# ctx.scene.render.filepath = join(RENDER_OUTPUT_DIR, args.model_filename_noext)
ctx.scene.render.filepath = args.output_file_path
print(f"Render output will be saved to: {args.output_file_path}")

# Ensure output directory exists
output_dir = os.path.dirname(args.output_file_path)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created output directory: {output_dir}")

# Move the camera so that the model fills the frame
bpy.ops.view3d.camera_to_view_selected()
# Zoom the camera back slightly to account for chromatic aberration
# If you remove chromatic aberration from the blender scene, either remove this line or set it to 50 (the default value)
bpy.data.cameras.values()[0].lens = 49
# Render the scene
bpy.ops.render.render(write_still=True)



##### CLEANUP #####

# Remove the material's pointer to the requested texture (will always be on the last line unless given an invalid material)
with open(args.material, "r") as f:
    lines = f.readlines()
with open(args.material, "w") as f:
    for line in lines[:-1]:
        f.write(line)
