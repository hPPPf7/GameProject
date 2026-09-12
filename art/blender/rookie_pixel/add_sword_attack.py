"""Extend the existing Rookie model through Blender MCP; never rebuild the character.

Run build_sword(), build_attack(), render_attack(), save_attack() in separate stages.
"""
from pathlib import Path
import importlib.util
import math
import json
import bpy
from mathutils import Vector, Matrix, Quaternion

ROOT = Path(r"D:\AI\code-0\舊的\GameProject\art\blender\rookie_pixel")
spec = importlib.util.spec_from_file_location("rookie_base", ROOT/"build_character.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
ATTACK = "AN_Rookie_Attack_Sword_01"
RIG = "ARM_Rookie"
SWORD_COL = "COL_Rookie_Sword"
GRIP = Vector((-.755,-.035,.935))


def material(name, color):
    name = "MAT_Sword_"+name
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    rgb = [int(color[i:i+2],16)/255 for i in (0,2,4)]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*linear,1)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    shader = m.node_tree.nodes.new("ShaderNodeEmission")
    shader.inputs["Color"].default_value = (*linear,1)
    out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
    m.node_tree.links.new(shader.outputs[0],out.inputs["Surface"])
    return m


def attach(obj, mat):
    base.put(obj,SWORD_COL)
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    vg = obj.vertex_groups.new(name="hand.R")
    vg.add(list(range(len(obj.data.vertices))),1,"REPLACE")
    mod = obj.modifiers.new("Right hand grip", "ARMATURE")
    mod.object = bpy.data.objects[RIG]
    obj.parent = bpy.data.objects[RIG]
    obj["bind_bone"] = "hand.R"
    obj["asset"] = "Rookie short sword"
    return obj


def sword_box(name,local,size,mat,bevel=.006):
    obj = base.box("Sword_"+name,GRIP+Vector(local),size,"leather",None,bevel)
    return attach(obj,mat)


def sword_mesh(name,verts,faces,mat):
    obj = base.mesh("Sword_"+name,[GRIP+Vector(v) for v in verts],faces,"leather")
    return attach(obj,mat)


def build_sword():
    base.activate()
    if SWORD_COL in bpy.data.collections:
        raise RuntimeError("Sword already exists; edit its meshes in place.")
    s = base.scene()
    s.collection.children.link(bpy.data.collections.new(SWORD_COL))
    (ROOT/"renders"/"attack").mkdir(parents=True,exist_ok=True)
    rig = bpy.data.objects[RIG]
    rig.data.pose_position = "REST"
    steel = material("Steel","A9BEC9")
    bright = material("Edge","EAF3EF")
    shadow = material("SteelShadow","687F94")
    gold = material("Guard","CBA264")
    gold_dark = material("GuardShadow","89643D")
    leather = material("Grip","343D50")
    band = material("Wrap","536279")
    blue = material("Gem","70A7BC")
    # Diamond section: broad faces are visible from the right-facing profile camera.
    verts=[]
    for z,w in ((.23,.095),(.37,.115),(1.04,.088)):
        verts += [(-.037,0,z),(0,-w,z),(.037,0,z),(0,w,z)]
    verts.append((0,0,1.24))
    faces=[(3,2,1,0)]
    for level in range(2):
        for i in range(4):faces.append((level*4+i,level*4+(i+1)%4,(level+1)*4+(i+1)%4,(level+1)*4+i))
    for i in range(4):faces.append((8+i,8+(i+1)%4,12))
    blade=sword_mesh("Blade",verts,faces,steel)
    blade.data.materials.append(bright)
    blade.data.materials.append(shadow)
    for p in blade.data.polygons:
        p.material_index = 1 if p.normal.y < -.1 else (2 if p.normal.x > .1 else 0)
    # Pixel-step crossguard and pommel, with a navy wrapped grip.
    outline=[(-.29,.16),(-.29,.24),(-.21,.24),(-.18,.20),(-.075,.22),(.075,.22),(.18,.20),(.21,.24),(.29,.24),(.29,.16),(.20,.13),(.12,.15),(-.12,.15),(-.20,.13)]
    gv=[(x,y,z) for x in (-.055,.055) for y,z in outline]
    n=len(outline)
    gf=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    guard=sword_mesh("Guard",gv,gf,gold)
    guard.data.materials.append(gold_dark)
    for p in guard.data.polygons:
        if p.normal.z<-.1:p.material_index=1
    sword_box("Handle",(0,0,-.015),(.095,.105,.28),leather)
    for i,z in enumerate((-.11,-.035,.04,.115)):
        sword_box("Wrap_"+str(i),(0,0,z),(.103,.113,.025),band,.002)
    sword_box("Pommel",(0,0,-.20),(.135,.16,.12),gold,.018)
    sword_box("PommelInset",(-.072,0,-.20),(.008,.074,.059),blue,0)
    sword_box("GuardGem",(-.065,0,.185),(.025,.105,.102),blue,.009)
    sword_box("BladeFuller",(-.038,0,.635),(.004,.016,.56),shadow,0)
    rig.data.pose_position = "POSE"
    for label,location in (("AttackSide",(-7,-.42,1.52)),("AttackHero",(-6,-4,2.8))):
        cam = base.camera("CAM_Rookie_"+label,location,(0,-.42,1.52),5.0)
        cam.data.lens = 50
    print("Sword created:",len(bpy.data.collections[SWORD_COL].objects),"parts, attached to hand.R")


# frame, wrist X/Y/Z, sword pitch, pelvis Y/Z, torso lean/yaw, free wrist X/Y/Z
KEY_POSES=[
    (1, (-.72,-.31,1.22), .48, (0,-.035), (.0,.0), (.64,-.13,1.04)),
    (5, (-.81,-.06,1.60), .02, (.015,-.065), (-.05,-.09), (.63,-.05,1.14)),
    (9, (-.82,.015,1.75), -.43, (.015,-.075), (-.07,-.13), (.63,.025,1.19)),
    (11,(-.80,-.14,1.69), .45, (-.025,-.070), (.025,-.025), (.66,.03,1.18)),
    (13,(-.67,-.49,1.38), 1.55, (-.06,-.080), (.12,.12), (.65,.06,1.16)),
    (16,(-.67,-.39,1.14), 2.11, (-.06,-.080), (.14,.14), (.65,.08,1.18)),
    (19,(-.70,-.32,1.12), 2.04, (-.045,-.070), (.09,.10), (.65,.015,1.14)),
    (25,(-.73,-.31,1.19), .84, (-.005,-.045), (.015,.025), (.64,-.10,1.06)),
    (31,(-.72,-.31,1.22), .48, (0,-.035), (.0,.0), (.64,-.13,1.04)),
]


def interpolate(frame):
    for a,b in zip(KEY_POSES,KEY_POSES[1:]):
        if a[0]<=frame<=b[0]:
            t=(frame-a[0])/(b[0]-a[0]);t=t*t*(3-2*t)
            return [tuple(x+(y-x)*t for x,y in zip(av,bv)) if isinstance(av,tuple) else av+(bv-av)*t for av,bv in zip(a[1:],b[1:])]
    raise ValueError(frame)


def aim_bone(rig,name,head,tail):
    b = rig.data.bones[name]
    direction=(tail-head).normalized()
    if name.startswith("upper_arm"):
        quat=(b.tail_local-b.head_local).rotation_difference(direction) @ b.matrix_local.to_quaternion()
    else:
        # A body-fixed roll axis avoids a sudden forearm twist as the blade
        # passes from raised to forward. The wrist has its own explicit rotation.
        axis=Vector((1,0,0))
        x_axis=(axis-direction*axis.dot(direction)).normalized()
        z_axis=x_axis.cross(direction).normalized()
        quat=Matrix((x_axis,direction,z_axis)).transposed().to_quaternion()
    rig.pose.bones[name].matrix = Matrix.LocRotScale(head,quat,Vector((1,1,1)))
    bpy.context.view_layer.update()


def arm_to(rig,side,wrist):
    upper,lower = "upper_arm."+side,"forearm."+side
    shoulder=rig.pose.bones[upper].head.copy()
    target=Vector(wrist)
    l1,l2=rig.data.bones[upper].length,rig.data.bones[lower].length
    delta=target-shoulder;direction=delta.normalized()
    distance=min(delta.length,l1+l2-.0002)
    target=shoulder+direction*distance
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    height=math.sqrt(max(0,l1*l1-along*along))
    sign=-1 if side=="R" else 1
    pole=Vector((sign*1.4,.20,1.25))-shoulder
    bend=(pole-direction*pole.dot(direction)).normalized()
    elbow=shoulder+direction*along+bend*height
    aim_bone(rig,upper,shoulder,elbow)
    aim_bone(rig,lower,elbow,target)
    return rig.pose.bones[lower].tail.copy()


def build_attack():
    base.activate()
    rig=bpy.data.objects[RIG]
    rig.data.pose_position="POSE"
    if ATTACK in bpy.data.actions:
        raise RuntimeError("Attack exists; use rebuild_attack() for this generated action.")
    old=rig.animation_data.action
    if old:old.use_fake_user=True
    rig.animation_data.action=None
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
    previous_rotations={}
    # Quarter-frame baking preserves the intended world-space grip between keys.
    for sample in range(121):
        frame=1+sample*.25
        # Author absolute poses instead of accumulating transformations.
        for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
        wrist,pitch,hip,torso,free=interpolate(frame)
        p=rig.pose.bones["pelvis"]
        p.location=rig.data.bones["pelvis"].matrix_local.to_3x3().inverted()@Vector((0,hip[0],hip[1]))
        # The legs stay planted in a staggered stance throughout the attack.
        for side,y in (("R",-.18),("L",.15)):
            b=rig.pose.bones["CTRL_foot."+side]
            b.location=rig.data.bones[b.name].matrix_local.to_3x3().inverted()@Vector((0,y,0))
        spine=rig.pose.bones["spine"]
        rest=rig.data.bones["spine"].matrix_local.to_quaternion()
        global_rot=Quaternion((0,0,1),torso[1])@Quaternion((1,0,0),torso[0])
        spine.rotation_quaternion=rest.inverted()@global_rot@rest
        bpy.context.view_layer.update()
        actual=arm_to(rig,"R",wrist)
        h=rig.pose.bones["hand.R"]
        desired=Quaternion((1,0,0),pitch)@rig.data.bones[h.name].matrix_local.to_quaternion()
        h.matrix=Matrix.LocRotScale(actual,desired,Vector((1,1,1)))
        bpy.context.view_layer.update()
        arm_to(rig,"L",free)
        # Slight counter rotation keeps the eyes on the target.
        head=rig.pose.bones["head"]
        head.rotation_quaternion=Quaternion((0,1,0),-torso[1]*.5)
        for b in rig.pose.bones:
            # q and -q encode the same pose, but interpolating between them can
            # spin the wrist almost 180 degrees between otherwise correct frames.
            if b.rotation_mode=="QUATERNION":
                rotation=b.rotation_quaternion.copy()
                if b.name in previous_rotations and rotation.dot(previous_rotations[b.name])<0:
                    rotation.negate()
                b.rotation_quaternion=rotation
            else:
                rotation=b.rotation_euler.copy()
                if b.name in previous_rotations:rotation.make_compatible(previous_rotations[b.name])
                b.rotation_euler=rotation
            previous_rotations[b.name]=rotation.copy()
            b.keyframe_insert("location",frame=frame)
            path="rotation_quaternion" if b.rotation_mode=="QUATERNION" else "rotation_euler"
            b.keyframe_insert(path,frame=frame)
    action=rig.animation_data.action
    action.name=ATTACK
    action.use_fake_user=True
    action["timing"]="30 fps; frames 1-9 anticipation, 10-13 strike, 14-19 follow-through, 20-30 recovery; frame 31 closes to frame 1"
    action["root_motion"]="In place; planted foot IK targets"
    s=base.scene();s.frame_start,s.frame_end=1,30;s.frame_set(1)
    # Named timing markers are useful when the user scrubs the timeline.
    for f,label in ((1,"Ready"),(5,"Raise sword"),(9,"Wind-up"),(13,"Strike"),(16,"Follow-through"),(25,"Recover")):
        m=s.timeline_markers.new("Sword / "+label,frame=f)
    print("Created",action.name,"frames",list(action.frame_range))


def rebuild_attack():
    rig=bpy.data.objects[RIG]
    old=bpy.data.actions.get(ATTACK)
    if old:
        if rig.animation_data.action==old:rig.animation_data.action=None
        bpy.data.actions.remove(old)
    for m in list(base.scene().timeline_markers):
        if m.name.startswith("Sword / "):base.scene().timeline_markers.remove(m)
    build_attack()


def render_attack(first=0,last=15,view="Side",width=160,height=128):
    base.activate()
    rig=bpy.data.objects[RIG];rig.data.pose_position="POSE"
    rig.animation_data.action=bpy.data.actions[ATTACK]
    s=base.scene();s.camera=bpy.data.objects["CAM_Rookie_Attack"+view]
    s.render.resolution_x,s.render.resolution_y=width,height
    for i in range(first,last):
        s.frame_set(1+2*i)
        s.render.filepath=str(ROOT/"renders"/"attack"/f"attack_{view.lower()}_{i:02d}.png")
        bpy.ops.render.render(write_still=True)
    print("Rendered",view,first,"to",last-1)


def save_attack():
    base.activate()
    s=base.scene();s.frame_start,s.frame_end=1,30;s.frame_set(1)
    bpy.data.objects[RIG].animation_data.action=bpy.data.actions[ATTACK]
    base.show_camera("CAM_Rookie_AttackHero")
    s.render.resolution_x,s.render.resolution_y=160,128
    bpy.ops.object.select_all(action="DESELECT")
    rig=bpy.data.objects[RIG];rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/"rookie_sword_attack.blend"))
    print("Saved",str(ROOT/"rookie_sword_attack.blend"))


def validate_attack():
    rig=bpy.data.objects[RIG];s=base.scene()
    ik=[];sole=[];tips=[];loop=[];previous={};angles=[];norms=[];tip_errors=[]
    footheads={"L":[],"R":[]}
    for step in range(121):
        f=1+step*.25
        s.frame_set(int(f),subframe=f-int(f))
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        for side in ("L","R"):
            foot=rig.pose.bones["foot."+side]
            target=rig.pose.bones["CTRL_foot."+side]
            ik.append((foot.head-target.head).length)
            footheads[side].append(foot.head.copy())
            ob=bpy.data.objects["SM_Rookie_Sole_"+side].evaluated_get(deps)
            sole.append(min((ob.matrix_world@v.co).z for v in ob.data.vertices))
        predicted=rig.pose.bones["hand.R"].matrix@rig.data.bones["hand.R"].matrix_local.inverted()@(GRIP+Vector((0,0,1.24)))
        blade=bpy.data.objects["SM_Rookie_Sword_Blade"].evaluated_get(deps)
        actual=blade.matrix_world@blade.data.vertices[12].co
        tip_errors.append((actual-predicted).length)
        tips.append(list(actual))
        for name in ("upper_arm.R","forearm.R","hand.R"):
            q=rig.pose.bones[name].matrix.to_quaternion()
            if name in previous:
                a=math.degrees(q.rotation_difference(previous[name]).angle)
                angles.append(min(a,360-a))
            previous[name]=q
        norms.append(rig.pose.bones["hand.R"].rotation_quaternion.magnitude)
        if step in (0,120):
            loop.append({b.name:[v for row in b.matrix for v in row] for b in rig.pose.bones})
    weapons=[o for o in bpy.data.collections[SWORD_COL].objects if o.type=="MESH"]
    triangles=0
    for o in weapons:
        o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    report={
        "attack":ATTACK,"blender_frames":30,"fps":30,"sheet_frames":15,"sheet_fps":15,
        "sword_meshes":len(weapons),"sword_triangles":triangles,
        "max_foot_ik_error":max(ik),"minimum_sole_bottom_z":min(sole),"maximum_sole_bottom_z":max(sole),
        "foot_drift":{side:max((p-ps[0]).length for p in ps) for side,ps in footheads.items()},
        "minimum_blade_tip_z":min(p[2] for p in tips),"maximum_blade_attachment_error":max(tip_errors),
        "loop_matrix_error":max(abs(a-b) for name in loop[0] for a,b in zip(loop[0][name],loop[1][name])),
        "max_arm_rotation_per_quarter_frame_deg":max(angles),"minimum_wrist_quaternion_norm":min(norms),
        "unweighted_sword_vertices":sum(not v.groups for o in weapons for v in o.data.vertices),
        "walk_action_preserved":"AN_Rookie_Walk_InPlace" in bpy.data.actions,
    }
    assert report["loop_matrix_error"]<1e-5
    assert report["max_foot_ik_error"]<.0001
    assert report["maximum_blade_attachment_error"]<.0001
    assert report["minimum_sole_bottom_z"]>-.0001
    assert report["minimum_wrist_quaternion_norm"]>.98
    assert report["max_arm_rotation_per_quarter_frame_deg"]<20
    (ROOT/"sword_attack_validation.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report))
    s.frame_set(1)
