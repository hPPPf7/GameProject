"""Run the stages through Blender MCP; all geometry is generated locally in Blender.

build_base() -> build_details() -> build_rig() -> render_view()/render_walk()
Re-load this file between stages. No scene or object outside this prototype is removed.
"""
from pathlib import Path
import bpy
import math
import random
import json
from mathutils import Vector

ROOT = Path(r"D:\AI\code-0\舊的\GameProject\art\blender\rookie_pixel")
SCENE_NAME = "Rookie_Pixel_Prototype"
PALETTE = {
    "skin": "F4CA96", "coat": "B38647", "coat_edge": "765334",
    "shirt": "27384C", "scarf": "304963", "hair": "8B847B",
    "hair_dark": "514B4A", "pants": "4B3B34", "boot": "67432B",
    "leather": "765033", "leather_edge": "493429", "buckle": "BA8B47",
    "eye": "25242C", "sole": "322D2C", "scarf_light": "405B75",
    "skin_shadow": "D69B70",
}


def scene():
    return bpy.data.scenes[SCENE_NAME]


def activate():
    bpy.context.window.scene = scene()


def put(obj, collection="COL_Rookie_Character"):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    bpy.data.collections[collection].objects.link(obj)
    return obj


def atlas_material():
    name = "MAT_Rookie_PixelAtlas"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    width, height, cell = 128, 96, 16
    img = bpy.data.images.new("T_Rookie_PixelAtlas", width=width, height=height, alpha=True)
    pixels = [0.0] * (width * height * 4)
    for group, (key, value) in enumerate(PALETTE.items()):
        rgb = [int(value[i:i+2], 16)/255 for i in (0, 2, 4)]
        for shade, factor in enumerate((0.78, 1.0, 1.10)):
            tile = group*3 + shade
            ox, oy = (tile % 8)*cell, (tile//8)*cell
            rng = random.Random(100 + group)
            patches = [(rng.randrange(1, 13), rng.randrange(2, 13), rng.randrange(2, 5), rng.randrange(2, 5)) for _ in range(3)]
            for y in range(cell):
                for x in range(cell):
                    patch = any(px <= x < px+pw and py <= y < py+ph for px, py, pw, ph in patches)
                    p = 0.94 if patch and key not in ("eye", "skin", "sole") else 1.0
                    color = [min(1.0, v*factor*p) for v in rgb]
                    i = ((oy+y)*width+ox+x)*4
                    pixels[i:i+4] = color + [1.0]
    img.pixels.foreach_set(pixels)
    img.update()
    img.filepath_raw = str(ROOT / "rookie_pixel_atlas.png")
    img.file_format = "PNG"
    img.save()
    img.pack()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"
    tex.location = (-300, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (-50, 0)
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (170, 0)
    mat.node_tree.links.new(tex.outputs["Color"], emission.inputs["Color"])
    mat.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    mat.diffuse_color = (0.55, 0.35, 0.16, 1)
    return mat


def paint(obj, color, bone=None):
    obj.data.materials.clear()
    obj.data.materials.append(atlas_material())
    uv = obj.data.uv_layers.get("UVMap") or obj.data.uv_layers.new(name="UVMap")
    # Blender's translated default UV name may be "UV貼圖". Explicitly select ours.
    uv.active_render = True
    obj.data.uv_layers.active = uv
    group = list(PALETTE).index(color)
    for face in obj.data.polygons:
        face.use_smooth = False
        normal = obj.matrix_world.to_3x3() @ face.normal
        light = normal.dot(Vector((-0.4, -0.65, 0.7)).normalized())
        shade = 2 if light > 0.60 else (0 if light < -0.20 else 1)
        if color in ("eye", "skin"):
            shade = 1 if light > -0.20 else 0
        face_group = group
        if obj.name == "SM_Rookie_Hair_Cap" and face.center.z < 2.22 and face.center.y > -.22:
            face_group = list(PALETTE).index("hair_dark")
        tile = face_group*3 + shade
        tx, ty = tile % 8, tile//8
        # Planar UV projection, kept a half texel inside each palette tile.
        axis = max(range(3), key=lambda i: abs(face.normal[i]))
        axes = [i for i in range(3) if i != axis]
        coords = [obj.data.vertices[obj.data.loops[li].vertex_index].co for li in face.loop_indices]
        lo = [min(v[a] for v in coords) for a in axes]
        hi = [max(v[a] for v in coords) for a in axes]
        for li, v in zip(face.loop_indices, coords):
            u = (v[axes[0]]-lo[0]) / max(hi[0]-lo[0], 1e-6)
            w = (v[axes[1]]-lo[1]) / max(hi[1]-lo[1], 1e-6)
            uv.data[li].uv = ((tx*16+0.5+15*u)/128, (ty*16+0.5+15*w)/96)
    obj["palette"] = color
    if bone:
        obj["bind_bone"] = bone
    obj.data.update()
    return obj


def box(name, loc, size, color, bone=None, bevel=0.025):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = put(bpy.context.object)
    obj.name = "SM_Rookie_" + name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Single chamfer", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return paint(obj, color, bone)


def segment(name, start, end, width, depth, color, bone, bevel=0.025):
    a, b = Vector(start), Vector(end)
    obj = box(name, (a+b)*0.5, (width, depth, (b-a).length), color, bone, bevel)
    obj.rotation_euler = (b-a).to_track_quat("Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return paint(obj, color, bone)


def mesh(name, vertices, faces, color, bone=None):
    data = bpy.data.meshes.new("ME_Rookie_"+name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new("SM_Rookie_"+name, data)
    bpy.data.collections["COL_Rookie_Character"].objects.link(obj)
    # Recalculate outward normals before selecting the discrete shade tiles.
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return paint(obj, color, bone)


def prism(name, outline, front, back, color, bone="head"):
    verts = [(x, front, z) for x,z in outline] + [(x, back, z) for x,z in outline]
    n = len(outline)
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name, verts, faces, color, bone)


def face_mesh():
    # The shallow angled cheeks let the same eye geometry show in front and profile.
    outline = [(-.17,-.45),(.17,-.45),(.53,-.275),(.53,.23),(.33,.34),(-.33,.34),(-.53,.23),(-.53,-.275)]
    verts = []
    for z, scale in [(1.635,.80),(1.755,1),(2.31,1),(2.42,.82)]:
        verts.extend([(x*scale,(y+.055)*scale-.055,z) for x,y in outline])
    faces = [tuple(reversed(range(8))),tuple(range(24,32))]
    for j in range(3):
        for i in range(8):
            faces.append((j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i))
    return mesh("Face",verts,faces,"skin","head")


def camera(name, loc, target, scale=3.15):
    data = bpy.data.cameras.new(name)
    data.type = "ORTHO"
    data.ortho_scale = scale
    obj = bpy.data.objects.new(name, data)
    bpy.data.collections["COL_Rookie_Studio"].objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def show_camera(name="CAM_Rookie_Hero"):
    s = scene()
    s.camera = bpy.data.objects[name]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.region_3d.view_camera_zoom = -10
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.shading.type = "MATERIAL"


def build_base():
    if SCENE_NAME in bpy.data.scenes:
        raise RuntimeError("Prototype already exists; resume its stages instead of rebuilding.")
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT/"renders").mkdir(exist_ok=True)
    s = bpy.data.scenes.new(SCENE_NAME)
    bpy.context.window.scene = s
    for name in ("COL_Rookie_Character", "COL_Rookie_Studio", "COL_Rookie_Rig", "COL_Rookie_Reference"):
        s.collection.children.link(bpy.data.collections.new(name))
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x = s.render.resolution_y = 128
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.render.film_transparent = True
    s.render.fps = 30
    s.render.filter_size = 0.01
    if hasattr(s, "eevee") and hasattr(s.eevee, "taa_render_samples"):
        s.eevee.taa_render_samples = 1
    if hasattr(s.render, "use_motion_blur"):
        s.render.use_motion_blur = False
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.world = bpy.data.worlds.new("WORLD_Rookie")
    s.world.color = (0.15, 0.15, 0.15)
    s.frame_start, s.frame_end = 1, 24
    camera("CAM_Rookie_Front", (0,-7,1.41), (0,0,1.41))
    camera("CAM_Rookie_Side", (-7,0,1.41), (0,0,1.41))
    camera("CAM_Rookie_Back", (0,7,1.41), (0,0,1.41))
    camera("CAM_Rookie_Hero", (4,-7,3.1), (0,0,1.40), 3.25)
    atlas_material()
    box("Torso", (0,0,1.21), (.78,.48,.64), "coat", "spine", .06)
    box("Coat_Hem", (0,.015,.91), (.88,.52,.30), "coat", "spine", .04)
    box("Shirt", (0,-.252,1.18), (.34,.035,.53), "shirt", "spine", 0)
    box("Belt", (0,-.28,.93), (.38,.04,.075), "leather", "pelvis", .005)
    box("Belt_Clasp", (0,-.305,.93), (.09,.014,.075), "buckle", "pelvis", 0)
    box("Hips", (0,0,.81), (.63,.40,.23), "pants", "pelvis", .025)
    box("Neck", (0,0,1.58), (.30,.29,.22), "skin", "head", .02)
    face_mesh()
    for side, sign in (("L",1),("R",-1)):
        x = sign*.22
        hip, knee, ankle = (x,0,.88),(x,-.045,.51),(x,0,.16)
        shoulder, elbow, wrist = (sign*.46,0,1.46),(sign*.65,-.015,1.19),(sign*.74,-.03,.98)
        segment("Thigh_"+side, hip,knee,.285,.35,"pants","thigh."+side,.025)
        segment("Shin_"+side, knee,ankle,.255,.29,"boot","shin."+side,.02)
        box("Boot_"+side,(x,-.09,.125),(.30,.49,.23),"boot","foot."+side,.035)
        box("Sole_"+side,(x,-.10,.025),(.32,.51,.05),"sole","foot."+side,.015)
        box("Boot_Cuff_"+side,(x,0,.36),(.285,.33,.11),"leather","shin."+side,.01)
        segment("Sleeve_Upper_"+side, shoulder,elbow,.32,.36,"coat","upper_arm."+side,.035)
        segment("Sleeve_Lower_"+side, elbow,wrist,.275,.31,"coat","forearm."+side,.025)
        segment("Cuff_"+side, Vector(wrist)+Vector((-sign*.015,0,.06)),Vector(wrist)+Vector((sign*.015,0,-.02)),.285,.32,"coat_edge","forearm."+side,.01)
        box("Hand_"+side,(sign*.755,-.035,.935),(.25,.25,.24),"skin","hand."+side,.055)
        box("Ear_"+side,(sign*.535,-.07,1.98),(.16,.22,.25),"skin_shadow","head",.035)
    # Packed reference image is available in the Image Editor; it is never rendered as geometry.
    ref = bpy.data.images.load(r"C:\Users\user\Downloads\7644fb54-0e4e-4a39-87a9-3b7ef5587027.png", check_existing=True)
    ref.name = "REFERENCE_User_Turnaround"
    ref.use_fake_user = True
    ref.pack()
    show_camera()
    print("Blockout created in a separate scene:", len(s.objects), "objects")


def build_details():
    activate()
    if "SM_Rookie_Hair_Cap" in bpy.data.objects:
        raise RuntimeError("Details already exist")
    # Hair is a real volume with a raised front hairline and a low nape.
    n = 12
    rings = []
    for level in range(4):
        ring = []
        for i in range(n):
            a = 2*math.pi*i/n
            if level == 0:
                rx, ry = .61,.46
                front = max(0,-math.sin(a))
                z = 1.88 + .43*front**3
            elif level == 1:
                rx,ry,z = .73,.54,2.35
            elif level == 2:
                rx,ry,z = .52,.40,2.61
            else:
                rx,ry,z = .18,.18,2.66
            ring.append((rx*math.cos(a), .015+ry*math.sin(a), z))
        rings.extend(ring)
    faces = []
    for level in range(3):
        for i in range(n):
            faces.append((level*n+i,level*n+(i+1)%n,(level+1)*n+(i+1)%n,(level+1)*n+i))
    faces += [tuple(reversed(range(n))),tuple(range(3*n,4*n))]
    mesh("Hair_Cap", rings, faces, "hair", "head")
    prism("Hair_Fringe_Left", [(-.69,2.41),(-.41,2.51),(-.20,2.39),(-.38,2.16),(-.39,2.27),(-.59,2.13),(-.58,2.23),(-.75,2.22)], -.535,-.34,"hair")
    prism("Hair_Fringe_Center", [(-.33,2.53),(-.04,2.55),(.14,2.43),(-.03,2.19),(-.10,2.19),(-.10,2.29),(-.32,2.15),(-.25,2.35)], -.565,-.38,"hair")
    prism("Hair_Fringe_Right", [(.02,2.55),(.34,2.53),(.62,2.40),(.58,2.19),(.44,2.14),(.43,2.33),(.24,2.20),(.19,2.37)], -.53,-.32,"hair")
    for side,sign in (("L",1),("R",-1)):
        outline = [(sign*x,z) for x,z in ((.53,2.38),(.72,2.34),(.72,2.06),(.58,1.92),(.49,1.99),(.52,2.17))]
        prism("Hair_Sideburn_"+side,outline,-.23,.06,"hair_dark")
        eye = box("Eye_"+side,(sign*.275,-.410,2.055),(.072,.014,.185),"eye","head",0)
        eye.rotation_euler.z = sign*math.atan(.175/.36)
    prism("Cowlick", [(-.06,2.63),(-.07,2.76),(-.22,2.85),(-.33,2.85),(-.32,2.79),(-.22,2.77),(-.19,2.62)], -.02,.14,"hair")
    box("Nose", (0,-.471,1.94), (.085,.06,.065),"skin","head",.01)
    # Broad collar, folded front, short hanging end: separate parts follow the chest.
    box("Scarf_Collar", (0,-.015,1.635), (.87,.65,.205),"scarf","spine",.04)
    prism("Scarf_FrontFold",[(-.43,1.70),(.44,1.70),(.34,1.54),(.02,1.48),(-.24,1.54)],-.38,-.30,"scarf","spine")
    box("Scarf_HangingEnd",(.20,-.30,1.32),(.17,.095,.37),"scarf","spine",.008)
    box("Scarf_EndBand",(.20,-.352,1.18),(.17,.012,.045),"scarf_light","spine",0)
    for side,sign in (("L",1),("R",-1)):
        outline = [(sign*x,z) for x,z in ((.12,1.51),(.34,1.50),(.43,1.31),(.33,1.18),(.22,1.32))]
        prism("Lapel_"+side,outline,-.294,-.24,"coat_edge","spine")
        box("Pocket_"+side,(sign*.32,-.287,.995),(.19,.04,.17),"coat","spine",.008)
        box("Pocket_Flap_"+side,(sign*.32,-.315,1.075),(.21,.016,.055),"coat_edge","spine",0)
        segment("Strap_Front_"+side,(sign*.34,-.28,1.52),(sign*.33,-.31,1.16),.087,.045,"leather","spine",.005)
        segment("Strap_Shoulder_"+side,(sign*.34,-.23,1.53),(sign*.34,.32,1.49),.10,.055,"leather","spine",.008)
        box("Strap_Buckle_"+side,(sign*.33,-.341,1.33),(.07,.02,.058),"buckle","spine",0)
    box("Backpack_Body",(0,.445,1.20),(.72,.39,.76),"leather","spine",.055)
    box("Backpack_Flap",(0,.57,1.465),(.77,.23,.28),"leather","spine",.035)
    box("Backpack_PocketBorder",(0,.65,1.08),(.49,.055,.32),"leather_edge","spine",.015)
    box("Backpack_Pocket",(0,.686,1.085),(.40,.045,.245),"leather","spine",.015)
    box("Backpack_ClaspStrap",(0,.704,1.33),(.10,.032,.29),"leather_edge","spine",.008)
    box("Backpack_Clasp",(0,.725,1.29),(.085,.015,.082),"buckle","spine",0)
    for side,sign in (("L",1),("R",-1)):
        box("Backpack_SidePocket_"+side,(sign*.377,.43,1.12),(.15,.25,.34),"leather_edge","spine",.025)
    show_camera()
    print("Details complete", len(bpy.data.collections["COL_Rookie_Character"].objects), "mesh objects")


def build_rig():
    activate()
    if "ARM_Rookie" in bpy.data.objects:
        raise RuntimeError("Rig already exists")
    bpy.ops.object.select_all(action="DESELECT")
    arm_data = bpy.data.armatures.new("ARM_Rookie_Skeleton")
    rig = bpy.data.objects.new("ARM_Rookie",arm_data)
    bpy.data.collections["COL_Rookie_Rig"].objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    rig.show_in_front = True
    bpy.ops.object.mode_set(mode="EDIT")
    def bone(name,head,tail,parent=None,connect=False,deform=True):
        b = arm_data.edit_bones.new(name)
        b.head,b.tail = head,tail
        if parent:
            b.parent = arm_data.edit_bones[parent]
        b.use_connect = connect
        b.use_deform = deform
        return b
    bone("root",(0,0,0),(0,0,.25),deform=False)
    bone("pelvis",(0,0,.80),(0,0,1.02),"root")
    bone("spine",(0,0,1.02),(0,0,1.60),"pelvis",True)
    bone("head",(0,0,1.60),(0,0,2.38),"spine",True)
    for side,sign in (("L",1),("R",-1)):
        x = sign*.22
        bone("thigh."+side,(x,0,.88),(x,-.045,.51),"pelvis")
        bone("shin."+side,(x,-.045,.51),(x,0,.16),"thigh."+side,True)
        bone("foot."+side,(x,0,.16),(x,-.25,.16),"shin."+side,True)
        bone("CTRL_foot."+side,(x,0,.16),(x,-.25,.16),"root",deform=False)
        bone("POLE_knee."+side,(x,-1,.50),(x,-1,.70),"root",deform=False)
        bone("upper_arm."+side,(sign*.46,0,1.46),(sign*.65,-.015,1.19),"spine")
        bone("forearm."+side,(sign*.65,-.015,1.19),(sign*.74,-.03,.98),"upper_arm."+side,True)
        bone("hand."+side,(sign*.74,-.03,.98),(sign*.76,-.04,.88),"forearm."+side,True)
    bpy.ops.object.mode_set(mode="OBJECT")
    for side in ("L","R"):
        ik = rig.pose.bones["shin."+side].constraints.new("IK")
        ik.name = "Foot plant IK"
        ik.target,ik.subtarget = rig,"CTRL_foot."+side
        ik.pole_target,ik.pole_subtarget = rig,"POLE_knee."+side
        ik.chain_count = 2
        ik.pole_angle = -math.pi/2
        ik.use_stretch = False
        rig.pose.bones["thigh."+side].ik_stretch = 0
        rig.pose.bones["shin."+side].ik_stretch = 0
        c = rig.pose.bones["foot."+side].constraints.new("COPY_ROTATION")
        c.target,c.subtarget = rig,"CTRL_foot."+side
        c.owner_space,c.target_space = "WORLD","WORLD"
    for obj in bpy.data.collections["COL_Rookie_Character"].objects:
        if obj.type != "MESH":
            continue
        name = obj.get("bind_bone")
        if not name:
            raise RuntimeError("Unassigned mesh: "+obj.name)
        vg = obj.vertex_groups.new(name=name)
        vg.add(list(range(len(obj.data.vertices))),1.0,"REPLACE")
        mod = obj.modifiers.new("Rookie skeleton", "ARMATURE")
        mod.object = rig
        obj.parent = rig
    # Keyframed IK targets keep the planted sole at Z=0, with a clear airborne swing.
    for f in range(1,26):
        t = (f-1)/24
        pelvis = rig.pose.bones["pelvis"]
        pelvis.location = arm_data.bones["pelvis"].matrix_local.to_3x3().inverted() @ Vector((0,0,-.047 + .012*math.cos(4*math.pi*t)))
        pelvis.keyframe_insert("location",frame=f)
        for side,phase in (("L",t%1),("R",(t+.5)%1)):
            ctrl = rig.pose.bones["CTRL_foot."+side]
            if phase < .5:
                y = -.22 + .88*phase
                lift = 0
            else:
                u = (phase-.5)*2
                y = .22 - .44*(3*u*u-2*u*u*u)
                lift = .16*math.sin(math.pi*u)
            delta = Vector((0,y,lift))
            ctrl.location = arm_data.bones[ctrl.name].matrix_local.to_3x3().inverted() @ delta
            ctrl.keyframe_insert("location",frame=f)
            upper = rig.pose.bones["upper_arm."+side]
            upper.rotation_mode = "XYZ"
            # Bone local X is close to the character's X: opposite arm/leg swing.
            upper.rotation_euler.x = .36*math.cos(2*math.pi*phase)
            upper.keyframe_insert("rotation_euler",frame=f)
            forearm = rig.pose.bones["forearm."+side]
            forearm.rotation_mode = "XYZ"
            forearm.rotation_euler.x = -.08 + .06*math.sin(2*math.pi*phase)
            forearm.keyframe_insert("rotation_euler",frame=f)
    action = rig.animation_data.action
    action.name = "AN_Rookie_Walk_InPlace"
    action.use_fake_user = True
    # Blender 5 actions may be layered; keyframe handles default to automatic Bezier.
    rig["rig_notes"] = "Foot targets + knee poles; in-place 24-frame walk at 30 fps. Rigid segmented prototype; no face controls."
    s = scene()
    s.frame_start,s.frame_end = 1,24
    s.frame_set(1)
    bpy.context.view_layer.update()
    print("Rig:",len(arm_data.bones),"bones. Walk:",action.name)
    print(json.dumps({side:{part:list(rig.pose.bones[part+'.'+side].head) for part in ('thigh','shin','foot','CTRL_foot')} for side in ('L','R')}))


def render_view(view="Hero", frame=1, size=128, filename=None, rest=False):
    activate()
    s = scene()
    rig = bpy.data.objects.get("ARM_Rookie")
    if rig:
        rig.data.pose_position = "REST" if rest else "POSE"
    s.frame_set(frame)
    s.camera = bpy.data.objects["CAM_Rookie_"+view]
    s.render.resolution_x = s.render.resolution_y = size
    s.render.filepath = str(ROOT/"renders"/(filename or f"{view.lower()}_{frame:02d}_{size}.png"))
    bpy.ops.render.render(write_still=True)
    if rig:
        rig.data.pose_position = "POSE"
    print(s.render.filepath)


def render_walk(first=0,last=8,view="Side"):
    for i in range(first,last):
        render_view(view,frame=1+3*i,size=96,filename=f"walk_{view.lower()}_{i:02d}.png")


def save_project():
    activate()
    scene().frame_set(1)
    show_camera()
    scene().render.resolution_x = scene().render.resolution_y = 128
    bpy.ops.object.select_all(action="DESELECT")
    rig = bpy.data.objects.get("ARM_Rookie")
    if rig:
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"rookie_pixel.blend"))
    print("Saved",str(ROOT/"rookie_pixel.blend"))
