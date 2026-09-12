# 菜鳥調查員：Blender 像素角色試作

依照使用者提供的三視圖，直接透過 Blender MCP 建立的可編輯立體角色。
所有幾何、骨架與動畫都在本機 Blender 製作。這是第一版風格與走路測試。

**目前狀態：保留試作，遊戲停用（2026-09-13）。** 遊戲固定使用 2D 原版，
不再提供版本切換。此資料夾的模型、骨架、動畫、渲染圖與腳本均保留。
本次工作已儲存至 `rookie_sword_attack.blend`，走路試作 `rookie_pixel.blend` 也保留。

## 持劍攻擊版

開啟 `rookie_sword_attack.blend`，在 3D 視窗按空白鍵播放攻擊。
本版在既有角色上增加一把銀灰劍身、金色護手、深色握柄的短劍，固定綁在右手。
攻擊動作是「抬劍蓄力 → 快速下劈 → 順勢收力 → 收劍回位」。

- `rookie_sword_attack_preview.gif`：正常速度，朝右側面與立體視角同步播放。
- `rookie_sword_attack_poses.png`：準備、蓄力、下劈與收勢四個姿勢。
- `rookie_sword_attack.png`：800 × 384 透明 sprite sheet，5 欄 × 3 排，每格 160 × 128。
- `rookie_sword_attack.animation.json`：15 格、15 FPS，可在既有檢查工具調速。
- `inspect_attack.ps1`：直接開啟攻擊 sprite sheet 檢查視窗。
- `add_sword_attack.py`、`make_attack_previews.py`：製作與輸出腳本。
- `sword_attack_validation.json`：接地、武器跟手、補幀轉向與首尾姿勢檢查。

動畫 `AN_Rookie_Attack_Sword_01` 在 30 FPS 下播放第 1–30 格，共 1 秒；
第 31 格是第 1 格的閉合姿勢。第 1–9 格蓄力，10–13 格出劍，14–19 格收勢，
20–30 格回位。sprite sheet 取第 1、3、5…29 格。
攻擊採原地踏穩的姿勢；腳掌 IK 固定，身體小幅轉動與降低重心。
劍位於 `COL_Rookie_Sword`，11 個網格、406 個三角形；由 `hand.R` 骨頭帶動。
既有角色的手、手臂仍採低多邊形分件結構，本版沒有新增敵人、傷害或遊戲碰撞。
走路試作仍可使用 `rookie_pixel.blend`。

## 開啟與預覽

- `rookie_pixel.blend`：模型、骨架、走路動畫、四個正交相機；已內嵌參考圖與貼圖。
- `rookie_turnaround.png`：正面、朝右側面、背面與立體視角。
- `rookie_walk_preview.gif`：朝右與立體視角的走路循環。
- `rookie_walk_3d.png`：384 × 192 透明 sprite sheet，4 欄 × 2 排，每格 96 × 96。
- `rookie_walk_3d.animation.json`：檢查工具設定，8 格、10 FPS。
- `inspect_preview.ps1`：以專案既有工具開啟這份 sprite sheet。

在 Blender 開啟 `rookie_pixel.blend` 後，使用 `Rookie_Pixel_Prototype` 場景。
3D 視窗按空白鍵播放／暫停，滑鼠中鍵可轉動觀察。
場景相機：`CAM_Rookie_Front`、`CAM_Rookie_Side`、`CAM_Rookie_Back`、`CAM_Rookie_Hero`。
`Side` 為嚴格側面，人物朝畫面右方；角色座標是 Z 向上、-Y 向前。
原本 Blender 的預設 `Scene` 也保留在同一份檔案中。

## 模型與動畫

- 62 個可分開調整的網格，合計 2,272 個三角形。
- 一張 128 × 96 像素圖集，Closest 取樣，使用色塊與分面明暗。
- 20 根骨架骨頭，包含左右腳 IK 控制與膝蓋方向控制。
- `AN_Rookie_Walk_InPlace`：原地走路，30 FPS 下 24 格（0.8 秒）。
- 第 25 格是第 1 格的閉合姿勢；正常播放範圍為 1–24，避免重複端點。
- sprite sheet 取 Blender 第 1、4、7、10、13、16、19、22 格，10 FPS。
- `CTRL_foot.L/R` 控制腳掌；`POLE_knee.L/R` 控制膝蓋方向。
- `pelvis` 是輕微身體起伏，手臂使用 FK 關鍵影格。

本版採分件、硬權重的低多邊形造型，沒有臉部表情骨架、布料模擬或完整關節皮膚。
髮型比參考圖更方正，衣服分件較明顯；若採用此方向，可以再修輪廓和關節銜接。
材質使用自帶明暗的像素圖集，方便穩定輸出；尚未做隨場景燈光變化的材質。
此模型渲染的 3D 風格動畫目前停用；遊戲使用 2D 原版的 `player_walk.png`。

## 保留的遊戲用輸出

曾供遊戲使用的 `idle.png`、`walk.png`、`attack.png` 保留在 `assets/characters/rookie_3d/`，
與上述早期預覽圖分開。三種動作統一使用朝右的立體正交視角、每格 128 × 96、
每 Blender 單位 30 像素，相機與角色原點固定，保留完整武器空間。
待機／走路／攻擊分別為 8 格 6 FPS、8 格 10 FPS、15 格 15 FPS。
待機以持劍準備姿勢加上輕微呼吸，走路與攻擊沿用原骨架動畫。

重新輸出的順序：

1. 在 Blender 開啟 `rookie_sword_attack.blend`。
2. 在 Blender Python 執行 `export_game_sprites.py`；其 `export_game_sprites()` 函式
   會輸出到 `renders/game/`，完成後恢復原相機、動畫與姿勢。
3. 在專案根目錄執行 `.\.venv\Scripts\python.exe art\blender\rookie_pixel\pack_game_sprites.py`，
   重新產生遊戲用 PNG 與 `.animation.json`。此步會將這三份動畫設定重設為預設速度與順序。
4. 使用 `inspect_sprites.ps1 assets\characters\rookie_3d\walk.png` 或對應的攻擊圖檢查輸出。
   目前遊戲固定使用 2D，重新輸出這些圖片不會啟用 3D。

遊戲仍以 Pygame 顯示平面圖片，不需要安裝 Blender 或額外的 3D 執行套件。

## 製作與檢查記錄

- `build_character.py`：MCP 分階段執行的建模腳本。
- `make_previews.py`：以 Pillow 合成 Blender 輸出，使用整數倍最近鄰放大。
- `renders/`：Blender 原始透明渲染。
- `validation.json`：模型統計、權重、接地與循環檢查。
- `brief.md`：參考圖分析與製作規格。

建模腳本須在 Blender 的 Python 環境執行。依序呼叫 `build_base()`、
`build_details()`、`build_rig()`；只在沒有此試作場景的新檔案中重建。
已有模型請直接編輯，避免重複建立。

驗證結果：所有頂點都有權重；首尾骨架矩陣完全相同；腳掌 IK 最大誤差
小於 0.00005 Blender 單位，腳底最低位置距地面小於 0.000006 單位。
sprite sheet 的 8 格各有不同影像，透明背景與分格設定已用專案載入器檢查。

工作流程參考：[arjun988/blender-skills](https://github.com/arjun988/blender-skills)。
