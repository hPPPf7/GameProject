# 劇情事件

## EV-001 (conditional)

你在村莊的簡報室收到任務指示。

**條件**: {"sanity": "S0"}

| 選項 | 結果 | 影響 |
| --- | --- | --- |
| 認真聽講 | 你獲得了基礎情資。 | fate:1 |
| 心不在焉 | 你沒怎麼聽懂內容。 |  |

## EV-007 (conditional)

你靠近村莊東牆，似乎聽見裂縫中的細語。

**條件**: {"sanity_in": ["S1", "S2"]}

| 選項 | 結果 | 影響 |
| --- | --- | --- |
| 靠近傾聽 | 聲音讓你不寒而慄。 | fate:1; sanity_change:S2; flag_set:flag_WhisperTrigger |
| 遠離此地 | 你決定裝作沒聽到。 |  |

## EV-021 (conditional)

鏡中映出不同樣貌的自己正凝視著你。

**條件**: {"sanity": "S2"}

| 選項 | 結果 | 影響 |
| --- | --- | --- |
| 伸手觸碰鏡中人 | 冰冷的觸感讓你更加迷惘。 | sanity_change:S2; flag_set:flag_seen_mirror_self |
| 大叫逃離 | 你慌張地跑出屋外。 | sanity_change:S1; flag_set:flag_seen_mirror_self |

## EV-025 (conditional)

你聽見自己的聲音在耳邊反覆低語。

**條件**: {"sanity": "S2", "flag_true": "flag_seen_mirror_self"}

| 選項 | 結果 | 影響 |
| --- | --- | --- |
| 閉上眼睛 | 聲音沒有停止，你感到意識模糊。 | sanity_change:S2 |
| 大喊住口 | 短暫的安靜後，一切更混亂。 | sanity_change:S2 |

## EV-014 (conditional)

村民忽然不斷重複同一句話。

**條件**: {"sanity": "S1", "flag_true": "flag_trust_made"}

| 選項 | 結果 | 影響 |
| --- | --- | --- |
| 跟著他說 | 你模仿他的語氣，開始分不清現實。 | sanity_change:S2 |
| 質疑他 | 他僵硬地停下動作。 |  |

## EV-016 (conditional)

湖面傳來與你相似的聲音在回響。

**條件**: {"sanity_in": ["S1", "S2"], "flag_true": "flag_WhisperTrigger"}

| 選項 | 結果 | 影響 |
| --- | --- | --- |
| 回應聲音 | 回音與你交談，你感到背脊發涼。 | sanity_change:S2 |
| 無視離開 | 你試著走遠，但聲音仍在腦中盤旋。 |  |

