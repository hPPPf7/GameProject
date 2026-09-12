"""Export matching Blender camera/scale/pivot for both existing game animations.

Execute export_game_sprites() through Blender MCP with the sword prototype open.
Only raw renders are written; the open Blender project and pose are restored.
"""
from pathlib import Path
import math
import bpy
from mathutils import Matrix, Vector

ROOT=Path(r"D:\AI\code-0\舊的\GameProject")
OUTPUT=ROOT/"art"/"blender"/"rookie_pixel"/"renders"/"game"


def export_game_sprites():
    s=bpy.data.scenes["Rookie_Pixel_Prototype"]
    rig=bpy.data.objects["ARM_Rookie"]
    previous_action=rig.animation_data.action
    previous_frame=s.frame_current
    previous_camera=s.camera
    previous_size=(s.render.resolution_x,s.render.resolution_y)
    previous_path=s.render.filepath
    previous_pose=rig.data.pose_position
    previous_basis={b.name:b.matrix_basis.copy() for b in rig.pose.bones}
    camera_data=bpy.data.cameras.new("CAM_Export_Rookie_Game")
    camera=bpy.data.objects.new("CAM_Export_Rookie_Game",camera_data)
    s.collection.objects.link(camera)
    camera_data.type="ORTHO"
    camera_data.ortho_scale=128/30  # native output: exactly 30 pixels per world unit
    camera.location=(-6,-4,2.8)
    target=Vector((0,-.30,1.42))
    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    try:
        s.camera=camera
        s.render.resolution_x,s.render.resolution_y=128,96
        rig.data.pose_position="POSE"
        for clip,count,step in (("idle",8,0),("walk",8,3),("attack",15,2)):
            action=bpy.data.actions["AN_Rookie_Walk_InPlace" if clip=="walk" else "AN_Rookie_Attack_Sword_01"]
            rig.animation_data.action=None
            for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
            rig.animation_data.action=action
            for i in range(count):
                s.frame_set(1+i*step)
                if clip=="idle":
                    # Gentle one-pixel breathing, based on the attack ready stance.
                    p=rig.pose.bones["pelvis"]
                    rise=.018*(1-math.cos(2*math.pi*i/count))
                    p.location+=rig.data.bones["pelvis"].matrix_local.to_3x3().inverted()@Vector((0,0,rise))
                    bpy.context.view_layer.update()
                s.render.filepath=str(OUTPUT/f"{clip}_{i:02d}.png")
                bpy.ops.render.render(write_still=True)
            print("Exported",clip,count,"frames")
    finally:
        rig.animation_data.action=None
        for b in rig.pose.bones:b.matrix_basis=previous_basis[b.name]
        rig.animation_data.action=previous_action
        rig.data.pose_position=previous_pose
        s.camera=previous_camera
        s.render.resolution_x,s.render.resolution_y=previous_size
        s.render.filepath=previous_path
        s.frame_set(previous_frame)
        bpy.data.objects.remove(camera,do_unlink=True)
        bpy.data.cameras.remove(camera_data)


if __name__=="__main__":
    export_game_sprites()
