# `story_data.json` 格式說明

每筆事件為一個 JSON 物件，事件資料組成一個陣列。

---

## ✅ 事件基本欄位

| 欄位名稱    | 型態 | 說明                                                       |
| ----------- | ---- | ---------------------------------------------------------- |
| `id`        | 字串 | 事件識別碼（唯一）                                         |
| `type`      | 字串 | 事件類型，如 `normal`、`battle`、`dialogue`、`conditional` |
| `text`      | 字串 | 事件描述（顯示在畫面文字區）                               |
| `condition` | 物件 | _可選_，僅 `conditional` 事件需指定條件                    |
| `options`   | 陣列 | 選項清單，每個選項為一個物件，包含 `text` 和 `effect`      |

---

## ✅ 事件類型 `type`

- `normal`：一般事件（例如走路遇到道具）
- `battle`：戰鬥事件，可能會造成扣血、提升能力
- `dialogue`：與角色互動事件，可影響命運值或觸發主線
- `conditional`：有條件的事件，需搭配 `condition` 欄位

---

## ✅ 選項欄位 `options`

每個選項包含：

- `text`：顯示給玩家的選項文字
- `effect`：玩家點選後造成的結果

### 常用 `effect` 欄位（可擴充）

| 欄位名稱        | 說明                       |
| --------------- | -------------------------- |
| `hp_change`     | 增減生命值（整數）         |
| `fate`          | 增減命運值                 |
| `atk`, `def`    | 增減能力值                 |
| `inventory_add` | 新增道具（填入名稱）       |
| `flag_set`      | 設定事件旗標（例：`true`） |

---

## ✅ 條件欄位 `condition`（僅 conditional 類型）

可用來控制該事件何時才會被抽到，例如：

```json
"condition": {
  "fate_min": 2
}
```

> 表示 `fate` 值 >= 2 才能觸發這個事件。

可支援的條件邏輯（未來可擴充）：

- `fate_min`：命運值大於等於某數
- `has_item`：背包中擁有某道具
- `flag_true`：某事件旗標為真

---

## ✅ 範例事件

```json
{
  "id": "event_normal_001",
  "type": "normal",
  "text": "你在荒野中撿到一個奇怪的石頭。",
  "options": [
    {
      "text": "撿起來",
      "effect": { "inventory_add": "奇怪的石頭" }
    },
    {
      "text": "無視它",
      "effect": {}
    }
  ]
}
```