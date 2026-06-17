# 菜鳥調查隊日誌

《菜鳥調查隊日誌》是一款以 Python 與 Pygame 製作的劇情調查遊戲。玩家扮演第一次被派上外勤的新人調查員，接下淺川村整村失聯的任務，帶著錄製器與簡報資料前往現場，逐步揭開異常現象、研究據點與「樣本#07」之間的真相。

遊戲以文字事件、選項決策、簡易戰鬥、背包道具與命運值變化推進。玩家的選擇會影響角色狀態、事件分支、紀錄內容與後續章節走向。

## 遊戲介紹

前哨站東北方的淺川村突然失聯，偵查用的傀儡也只回傳錯碼。你被隊長派往現場，原本看似普通的調查任務，很快變成一連串無法用常識解釋的異常事件。

在荒野、村莊、研究據點與終端觀測室之間，玩家會遇見發熱的石頭、結晶化的村民、詭異的投影、失控的實驗體，以及不斷指向自身身分的線索。任務的核心不只是「村民為什麼失聯」，還包括「你究竟是誰」。

## 核心玩法

- 閱讀事件文本，根據當下狀況選擇行動。
- 透過選項改變命運值、旗標、背包道具與章節進度。
- 在戰鬥事件中選擇攻擊、撤退或其他特殊行動。
- 透過任務紀錄與事件回報追蹤調查過程。
- 隨章節推進，逐步進入淺川村、研究據點與核心機組。

## 遊戲特色

- **劇情分支**：事件資料以 `data/story_data.json` 管理，選項可觸發不同結果、文字變體與章節跳轉。
- **命運系統**：玩家行動會改變命運傾向，影響事件敘事語氣與後續發展。
- **調查紀錄**：遊戲會保留文字紀錄，呈現玩家的選擇、回報與任務過程。
- **戰鬥事件**：部分事件會進入戰鬥流程，讓調查過程帶有風險與資源壓力。
- **桌面與 Android 打包**：專案提供 PyInstaller 與 Buildozer 設定，可輸出 Windows 執行檔或 Android 測試版。

## 技術概覽

遊戲會載入 `data/story_data.json` 的劇情資料，搭配 `assets/` 內的圖片、字型與音效資源，透過事件系統、戰鬥系統、命運系統與玩家狀態管理推進流程。

## 專案結構

```text
.
├── main.py                 # 遊戲入口、主迴圈、音樂與流程控制
├── ui_manager.py           # 介面繪製與互動區域
├── event_manager.py        # 劇情事件載入與選項處理
├── event_result_handler.py # 事件結果套用
├── battle_system.py        # 戰鬥流程
├── fate_system.py          # 事件後狀態更新
├── save_manager.py         # 存檔管理
├── settings_manager.py     # 設定管理
├── paths.py                # 資源路徑與使用者資料路徑
├── data/                   # 劇情資料
└── assets/                 # 圖片、字型、音效與背景素材
```

## 開發環境

建議使用 Python 3.10 以上版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install pygame
```

若要建立 Windows 執行檔，還需要安裝 PyInstaller：

```powershell
python -m pip install pyinstaller
```

## 執行遊戲

在專案根目錄執行：

```powershell
python main.py
```

遊戲會自動從專案內的 `assets/` 與 `data/` 讀取資源。開發模式下，存檔、設定與錯誤紀錄會寫入使用者資料目錄：

```text
%LOCALAPPDATA%\GameProject
```

若沒有 `LOCALAPPDATA`，則會改用使用者家目錄下的 `GameProject`。

## 建置 Windows 版

可以使用內建的建置腳本：

```powershell
.\build.ps1
```

或直接執行 Python 建置腳本：

```powershell
python build_game.py
```

完成後，輸出檔會位於 `dist/`。`build_game.py` 預設輸出名稱為 `InvestigationDiary.exe`。

打包後的版本會將使用者資料寫到執行檔旁的 `userdata/` 目錄，方便攜帶與發佈。

## 建置 Android 版

專案包含 `buildozer.spec`，設定如下：

- App 名稱：`菜鳥調查隊日誌`
- Package：`org.gameproject.investigationdiary`
- Android API：35
- 最低 Android API：23
- 架構：`arm64-v8a`
- 主要依賴：`python3==3.10.12`、`pygame`

在支援 Buildozer 的環境中可執行：

```bash
buildozer android debug
```

專案也提供 `build_android.sh` 作為 Android 建置輔助腳本。

## 劇情與素材

- 劇情資料集中在 `data/story_data.json`。
- 遊戲圖片、角色圖、背景、字型與音效放在 `assets/`。
- `buildozer.spec` 會封裝 `py`、`json`、`png`、`jpg`、`jpeg`、`ttf`、`wav`、`mp3` 等檔案。

更新劇情或素材後，請至少以開發模式執行一次 `python main.py`，確認資源路徑、文字顯示與音效載入正常。

## 常見問題

### 啟動時找不到圖片、字型或音效

請確認是從專案根目錄執行 `python main.py`，且 `assets/` 目錄存在。

### PyInstaller 打包後找不到資料檔

請使用 `build_game.py` 或 `build.ps1`，它們會將 `assets/` 與 `data/` 一起加入打包命令。

### 遊戲發生未處理錯誤

遊戲會將未處理例外寫入 `crash.log`。開發模式下可到 `%LOCALAPPDATA%\GameProject\crash.log` 查看。

