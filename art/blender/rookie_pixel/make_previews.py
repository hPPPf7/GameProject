"""Assemble Blender's rendered frames; no AI reference image is modified.

Requires Pillow. Nearest-neighbor integer enlargement preserves the native pixels.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
RENDERS = ROOT / "renders"
BG = (237, 232, 218)
INK = (47, 55, 54)
MUTED = (104, 109, 99)
ACCENT = (105, 133, 113)


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/msjh.ttc", size)


def background(size):
    out = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(out)
    for x in range(0, size[0], 24):
        for y in range(0, size[1], 24):
            d.point((x,y),fill=(216,215,200))
    return out


def sprite(name):
    return Image.open(RENDERS/name).convert("RGBA")


def place(canvas, image, xy, scale=3):
    enlarged = image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
    canvas.paste(enlarged,xy,enlarged)


def turnaround():
    out = background((1280,506))
    d = ImageDraw.Draw(out)
    d.text((32,20),"菜鳥調查員 / Blender 像素角色試作",font=font(25),fill=INK)
    d.text((32,58),"立體模型 · 像素貼圖 · 固定正交視角",font=font(15),fill=MUTED)
    d.line((32,88,1248,88),fill=ACCENT,width=2)
    for i,(name,label) in enumerate((("front","正面"),("side","朝右側面"),("back","背面"),("hero","立體視角"))):
        # A 128px render is cropped only at the empty horizontal margins.
        im = sprite(name+".png").crop((14,0,114,128))
        place(out,im,(40+310*i,99),3)
        d.text((157+310*i,479),label,font=font(16),fill=INK,anchor="mm")
    out.save(ROOT/"rookie_turnaround.png")


def walking():
    frames = []
    sheet = Image.new("RGBA",(96*4,96*2),(0,0,0,0))
    for i in range(8):
        out = background((720,416))
        d = ImageDraw.Draw(out)
        d.text((24,16),"菜鳥調查員 / 走路測試",font=font(23),fill=INK)
        d.text((24,51),"8 格循環 · 10 FPS · 96 px 原始輸出",font=font(14),fill=MUTED)
        for j,view in enumerate(("side","hero")):
            im = sprite(f"walk_{view}_{i:02d}.png")
            px = 34+j*350
            d.line((px+25,359,px+270,359),fill=(191,197,180),width=1)
            place(out,im,(px,88),3)
            d.text((px+145,390),"朝右走路" if j==0 else "立體視角",font=font(16),fill=INK,anchor="mm")
        d.rectangle((626,28,682,45),outline=ACCENT,width=1)
        d.rectangle((628,30,628+round(52*(i+1)/8),43),fill=ACCENT)
        frames.append(out)
        sheet.paste(sprite(f"walk_side_{i:02d}.png"),((i%4)*96,(i//4)*96))
    # Use one shared palette to avoid color flicker between GIF frames.
    montage = Image.new("RGB",(720,416*8))
    for i,im in enumerate(frames):
        montage.paste(im,(0,i*416))
    palette = montage.quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    gif = [im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    gif[0].save(ROOT/"rookie_walk_preview.gif",save_all=True,append_images=gif[1:],duration=100,loop=0,disposal=2,optimize=False)
    frames[0].save(ROOT/"rookie_walk_preview.png")
    sheet.save(ROOT/"rookie_walk_3d.png")
    (ROOT/"rookie_walk_3d.animation.json").write_text(json.dumps({"columns":4,"rows":2,"fps":10,"frame_order":list(range(1,9)),"offsets":{}},indent=2)+"\n",encoding="utf-8")
    out = background((96*4*3,96*2*3+60))
    place(out,sheet,(0,60),3)
    ImageDraw.Draw(out).text((20,15),"走路循環 / 01 → 08",font=font(22),fill=INK)
    out.save(ROOT/"rookie_walk_contact_sheet.png")


if __name__ == "__main__":
    turnaround()
    walking()
    print("Created turnaround, walking GIF, and inspector-compatible sprite sheet.")
