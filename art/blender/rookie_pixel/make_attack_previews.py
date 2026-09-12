"""Present Blender sword renders using exact integer pixel enlargement."""
from pathlib import Path
import json
from PIL import Image, ImageDraw
from make_previews import background, font, place, INK, MUTED, ACCENT

ROOT=Path(__file__).resolve().parent
RENDERS=ROOT/"renders"/"attack"


def load(view,index):
    return Image.open(RENDERS/f"attack_{view}_{index:02d}.png").convert("RGBA")


def build():
    frames=[]
    sheet=Image.new("RGBA",(800,384))
    for i in range(15):
        out=background((1024,520))
        d=ImageDraw.Draw(out)
        stage="抬劍蓄力" if i<5 else ("快速下劈" if i<7 else ("順勢收力" if i<10 else "收劍回位"))
        d.text((24,15),"菜鳥調查員 / 揮劍攻擊",font=font(24),fill=INK)
        d.text((24,53),"右手持劍 · 固定腳步 · 15 格 / 1 秒",font=font(15),fill=MUTED)
        d.text((860,22),stage,font=font(20),fill=ACCENT)
        d.line((24,82,1000,82),fill=ACCENT,width=2)
        for j,view in enumerate(("side","hero")):
            x=24+500*j
            d.line((x+65,436,x+355,436),fill=(191,197,180),width=1)
            place(out,load(view,i),(x,96),3)
            d.text((x+235,490),"朝右側面" if j==0 else "立體視角",font=font(16),fill=INK,anchor="mm")
        frames.append(out)
        sheet.paste(load("side",i),((i%5)*160,(i//5)*128))
    montage=Image.new("RGB",(1024,520*15))
    for i,frame in enumerate(frames):montage.paste(frame,(0,i*520))
    palette=montage.quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    indexed=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    # GIF timing uses centiseconds: 60+70+70ms for each three source frames.
    durations=[60 if i%3==0 else 70 for i in range(15)]
    indexed[0].save(ROOT/"rookie_sword_attack_preview.gif",save_all=True,append_images=indexed[1:],duration=durations,loop=0,disposal=2,optimize=False)
    frames[6].save(ROOT/"rookie_sword_attack_preview.png")
    sheet.save(ROOT/"rookie_sword_attack.png")
    (ROOT/"rookie_sword_attack.animation.json").write_text(json.dumps({"columns":5,"rows":3,"fps":15,"frame_order":list(range(1,16)),"offsets":{}},indent=2)+"\n",encoding="utf-8")
    contact=background((1280,376))
    d=ImageDraw.Draw(contact)
    d.text((24,14),"持劍姿勢 / 蓄力 → 下劈 → 收勢",font=font(22),fill=INK)
    for j,(i,label) in enumerate(((0,"準備"),(4,"蓄力"),(6,"下劈"),(8,"收勢"))):
        place(contact,load("hero",i),(j*320,60),2)
        d.text((j*320+160,350),label,font=font(17),fill=INK,anchor="mm")
    contact.save(ROOT/"rookie_sword_attack_poses.png")
    print("Created sword GIF, pose plate, and 15-frame transparent sprite sheet.")


if __name__=="__main__":
    build()
