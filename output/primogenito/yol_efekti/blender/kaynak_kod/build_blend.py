"""Builds an editable Blender project of the 'green road streaks' effect.
Usage: python3 build_blend.py <out.blend> <video filename next to the .blend>
Same streak set / ground line / speeds as streaks.py (1 Blender unit = 100 px, ortho camera = exact 1080x1920)."""
import math, os, sys
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import streaks as S                      # reuses STREAKS (seeded), GROUND, colours

OUT, VIDEO = sys.argv[1], sys.argv[2]
W, H, FPS, N = 1080, 1920, 30, S.n
PX = 0.01                                # pixels -> Blender units


def wx(x):
    return x * PX - W * PX / 2


def wy(y):
    return H * PX / 2 - y * PX


def lin(c):                               # sRGB 0-255 -> linear 0-1
    out = []
    for v in c:
        v /= 255
        out.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.name = "Yol_Cizgileri"
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, N
sc.render.engine = "BLENDER_EEVEE"
sc.view_settings.view_transform = "Standard"          # keep the footage's colours untouched
sc.render.film_transparent = True
if hasattr(sc.render.image_settings, "media_type"):
    sc.render.image_settings.media_type = "VIDEO"
sc.render.image_settings.file_format = "FFMPEG"
sc.render.ffmpeg.format = "MPEG4"; sc.render.ffmpeg.codec = "H264"
sc.render.filepath = "//render/arac_yol_yesil_cizgiler_"

# collections: footage / lights (rendered on separate view layers, merged in the compositor)
col_video = bpy.data.collections.new("Video"); sc.collection.children.link(col_video)
col_light = bpy.data.collections.new("Isik_Cizgileri"); sc.collection.children.link(col_light)

# camera
cam = bpy.data.objects.new("Kamera", bpy.data.cameras.new("Kamera"))
cam.data.type = "ORTHO"; cam.data.ortho_scale = H * PX; cam.location = (0, 0, 10)
sc.collection.objects.link(cam); sc.camera = cam

# footage plane
mesh = bpy.data.meshes.new("Video_Plane")
mesh.from_pydata([(-W * PX / 2, -H * PX / 2, 0), (W * PX / 2, -H * PX / 2, 0), (W * PX / 2, H * PX / 2, 0), (-W * PX / 2, H * PX / 2, 0)], [], [(0, 1, 2, 3)])
mesh.uv_layers.new(name="UV")
for li, uv in zip(mesh.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
    mesh.uv_layers["UV"].data[li.index].uv = uv
vplane = bpy.data.objects.new("Video", mesh); col_video.objects.link(vplane)
mat = bpy.data.materials.new("Video_Mat"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.load(f"//{VIDEO}" if False else os.path.abspath(VIDEO), check_existing=True)
img.source = "MOVIE"
img.colorspace_settings.name = "sRGB"            # footage is sRGB
img.filepath = f"//{os.path.basename(VIDEO)}"          # relative: keep the video next to the .blend
tex.image = img
tex.image_user.frame_duration = N; tex.image_user.frame_start = 1; tex.image_user.use_auto_refresh = True
em = nt.nodes.new("ShaderNodeEmission"); outn = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], outn.inputs["Surface"])
mesh.materials.append(mat)

# streak materials (shared strength keyframed for the 0.35 s fade-in)
mats = {}
for name, c in (("Yesil", S.LIGHT), ("Mint", S.MINT), ("Beyaz", S.WHITE)):
    m = bpy.data.materials.new(f"Cizgi_{name}"); m.use_nodes = True
    t = m.node_tree; t.nodes.clear()
    e = t.nodes.new("ShaderNodeEmission"); o = t.nodes.new("ShaderNodeOutputMaterial")
    e.inputs["Color"].default_value = lin(c)
    t.links.new(e.outputs[0], o.inputs["Surface"])
    for f, v in ((1, 0.0), (11, 1.0)):
        e.inputs["Strength"].default_value = v; e.inputs["Strength"].keyframe_insert("default_value", frame=f)
    mats[tuple(c)] = m

# streaks: tapered quads, location + thickness keyframed every frame (CONSTANT so the wrap-around is a clean jump)
for k, s in enumerate(S.STREAKS):
    L, th = s["L"], s["th"]
    me = bpy.data.meshes.new(f"Cizgi_{k:02d}")
    me.from_pydata([(0, 0, 0), ((L - th * 3) * PX, th / 2 * PX, 0), (L * PX, 0, 0), ((L - th * 3) * PX, -th / 2 * PX, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(mats[tuple(s["col"])])
    ob = bpy.data.objects.new(f"Cizgi_{k:02d}", me); col_light.objects.link(ob)
    for i in range(N):
        g = S.GROUND[i]; span = H - g
        y = g + 10 + s["v"] * (span - 10)
        per = W + L + 400
        x = (s["ph"] + s["speed"] * i) % per - L - 200
        ob.location = (wx(x), wy(y), 0.02)
        ob.scale = (1, 0.6 + 0.4 * span / 620, 1)
        ob.keyframe_insert("location", frame=i + 1); ob.keyframe_insert("scale", frame=i + 1)
    for fc in ob.animation_data.action.layers[0].strips[0].channelbags[0].fcurves if hasattr(ob.animation_data.action, "layers") else ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"

# under-glow: gradient plane whose top edge rides the ground line
ug_h = 700
me = bpy.data.meshes.new("Alt_Isik")
me.from_pydata([(-W * PX / 2, -ug_h * PX, 0), (W * PX / 2, -ug_h * PX, 0), (W * PX / 2, 0, 0), (-W * PX / 2, 0, 0)], [], [(0, 1, 2, 3)])
ug = bpy.data.objects.new("Alt_Isik", me); col_light.objects.link(ug)
m = bpy.data.materials.new("Alt_Isik_Mat"); m.use_nodes = True
t = m.node_tree; t.nodes.clear()
tc = t.nodes.new("ShaderNodeTexCoord"); sep = t.nodes.new("ShaderNodeSeparateXYZ")
inv = t.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
mul = t.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = -ug_h / 140
ex = t.nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"
amt = t.nodes.new("ShaderNodeMath"); amt.operation = "MULTIPLY"; amt.inputs[1].default_value = 0.30
em = t.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = lin((26, 217, 128))   # same tint as the clip
tr = t.nodes.new("ShaderNodeBsdfTransparent"); mix = t.nodes.new("ShaderNodeMixShader"); o = t.nodes.new("ShaderNodeOutputMaterial")
t.links.new(tc.outputs["Generated"], sep.inputs[0]); t.links.new(sep.outputs["Y"], inv.inputs[1])
t.links.new(inv.outputs[0], mul.inputs[0]); t.links.new(mul.outputs[0], ex.inputs[0]); t.links.new(ex.outputs[0], amt.inputs[0])
t.links.new(amt.outputs[0], mix.inputs["Fac"]); t.links.new(tr.outputs[0], mix.inputs[1]); t.links.new(em.outputs[0], mix.inputs[2])
t.links.new(mix.outputs[0], o.inputs["Surface"])
for f, v in ((1, 0.0), (11, 0.30)):
    amt.inputs[1].default_value = v; amt.inputs[1].keyframe_insert("default_value", frame=f)
me.materials.append(m)
for i in range(N):
    ug.location = (0, wy(S.GROUND[i] - 6), 0.01); ug.keyframe_insert("location", frame=i + 1)

# view layers: "Video" renders only the footage, "Isiklar" only the lights
vl_video = sc.view_layers[0]; vl_video.name = "Video"
vl_light = sc.view_layers.new("Isiklar")
for vl, keep in ((vl_video, "Video"), (vl_light, "Isik_Cizgileri")):
    for lc in vl.layer_collection.children:
        lc.exclude = lc.name != keep

# compositor: lights -> glare (bloom) -> screen over footage
ng = bpy.data.node_groups.new("Kompozit", "CompositorNodeTree")
sc.compositing_node_group = ng
ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
rv = ng.nodes.new("CompositorNodeRLayers"); rv.layer = "Video"; rv.location = (-500, 200)
rl = ng.nodes.new("CompositorNodeRLayers"); rl.layer = "Isiklar"; rl.location = (-500, -150)
gl = ng.nodes.new("CompositorNodeGlare"); gl.location = (-200, -150)
gl.inputs["Type"].default_value = "Fog Glow"
gl.inputs["Threshold"].default_value = 0.0
gl.inputs["Strength"].default_value = 1.0
gl.inputs["Quality"].default_value = "High" if False else gl.inputs["Quality"].default_value
mx = ng.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "SCREEN"; mx.location = (100, 0)
mx.inputs[0].default_value = 1.0
go = ng.nodes.new("NodeGroupOutput"); go.location = (350, 0)
ng.links.new(rl.outputs["Image"], gl.inputs["Image"])
ng.links.new(rv.outputs["Image"], mx.inputs[6]); ng.links.new(gl.outputs["Image"], mx.inputs[7])
ng.links.new(mx.outputs[2], go.inputs[0])

sc.render.engine = "CYCLES"                            # tested engine; emission-only scene renders fast
sc.cycles.samples = 16
sc.cycles.use_denoising = False
sc.frame_set(76)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), relative_remap=True)
print("saved", OUT)
