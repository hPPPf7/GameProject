"""Pack Blender renders into the production asset folder using pygame only."""
from pathlib import Path
import json
import pygame

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(__file__).resolve().parent/"renders"/"game"
DEST=ROOT/"assets"/"characters"/"rookie_3d"


def pack():
    DEST.mkdir(parents=True,exist_ok=True)
    for clip,count,columns,fps in (("idle",8,4,6),("walk",8,4,10),("attack",15,5,15)):
        rows=count//columns
        sheet=pygame.Surface((128*columns,96*rows),pygame.SRCALPHA)
        for i in range(count):
            frame=pygame.image.load(str(SOURCE/f"{clip}_{i:02d}.png"))
            assert frame.get_size()==(128,96)
            b=frame.get_bounding_rect(min_alpha=128)
            assert b.left>0 and b.top>0 and b.right<128 and b.bottom<96,(clip,i,b)
            sheet.blit(frame,((i%columns)*128,(i//columns)*96))
        pygame.image.save(sheet,str(DEST/f"{clip}.png"))
        (DEST/f"{clip}.animation.json").write_text(json.dumps({"columns":columns,"rows":rows,"fps":fps,"frame_order":list(range(1,count+1)),"offsets":{}},indent=2)+"\n",encoding="utf-8")
    print("Packed idle, walk, attack at",DEST)


if __name__=="__main__":
    pack()
