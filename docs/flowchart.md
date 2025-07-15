# 遊戲流程圖

```mermaid
graph TD
    S((起點)) --> M[進入遊戲主畫面]
    M --> click[點擊前進按鈕]
    click --> event{隨機事件}
    event --> normal[普通事件]
    event --> battle[戰鬥事件]
    event --> dialogue[對話事件]
    event --> cond[條件事件]
    normal --> process[處理事件結果]
    battle --> process
    dialogue --> process
    cond --> process
    process --> story{主線條件達成?}
    story -- 否 --> click
    story -- 是 --> mainline[觸發主線劇情]
    mainline --> endingCheck{結局條件?}
    endingCheck -- 否 --> click
    endingCheck -- 是 --> ending[進入結局劇情]
    ending --> replay{再次遊玩?}
    replay -- 是 --> M
    replay -- 否 --> E((結束))
```

此流程圖以 Mermaid 繪製，描繪遊戲從起點到結局的主要循環與判定。
