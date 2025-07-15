# Sanity 與 Flag 聯動控制表

這份表格提供設計師在編寫劇情事件時，如何以 **Sanity 狀態** 搭配 **旗標** 控制分支。

| 編號 | Sanity 狀態  | 需要的 Flag                     | 可觸發事件/變化            | 描述與效果                                  |
| ---- | ------------ | ------------------------------- | -------------------------- | ------------------------------------------- |
| 01   | S1（不穩定） | 無                              | EV-007：牆壁在說話         | 出現牆壁低語，開啟幻聽相關支線              |
| 02   | S2（崩潰）   | 無                              | EV-021：鏡中他不是你       | 鏡中出現異常主角影像，對話揭露身分謎團      |
| 03   | S1           | `flag_trust_made = true`        | EV-014：村民語句重複化     | 村民對你產生強烈 déjà vu 感，引導你懷疑世界 |
| 04   | S2           | `flag_seen_mirror_self = true`  | EV-025：主角語錄混亂       | 主角出現雙重語言，UI 出現錯誤訊息           |
| 05   | S1 或 S2     | `flag_WhisperTrigger = true`    | EV-016：湖邊回音           | 從湖中聽見「另一個自己」說話                |
| 06   | S0           | `flag_question_identity = true` | EV-018：村民口誤叫錯你名字 | 初步懷疑自己是替代者                        |
| 07   | S2           | `flag_trust_made = false`       | EV-030：模擬器重置事件     | 強制進入虛假結局，回到 Day 1                |
| 08   | 任意         | `flag_fate_over_10 = true`      | EV-040：命運閾值突破異象   | 出現錯誤選項或異世界生物                    |
| 09   | S2           | `flag_self_reflect = true`      | EV-033：分裂測試啟動       | 進入真結局候選區                            |

## 事件標註模板

```markdown
### ID：EV-021「鏡中他不是你」

**Sanity 條件**：S2
**需要 Flag**：flag_seen_mirror_self = false
**結果**：

- 設定 flag_seen_mirror_self = true
- 顯示選項「A. 伸手觸碰」「B. 不理它」
```

## 推薦 Flag 命名規則

- 敘事進程：`flag_mirror_seen`、`flag_first_dream`
- 角色伏筆：`flag_question_identity`、`flag_self_reflect`
- 分支導向：`flag_trust_made`、`flag_abandoned_village`
- 結局觸發：`flag_true_end_ready`、`flag_loop_triggered`

## UI 提示策略範例

- **Sanity = S2** 且 `flag_self_reflect = true`：畫面閃爍並出現「我是…我不是…？」
- **Sanity = S1** 且 `flag_trust_made = false`：村民不願再與你交談，但你聽見牆角有人在咕噥。
