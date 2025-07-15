# 遊戲流程圖

```mermaid
graph TD
    classDef startEnd fill:#f5f5f5,stroke:#333,stroke-width:2px;
    classDef mainNode fill:#d0e6ff,stroke:#333,stroke-width:2px;
    classDef decision fill:#ffe0b2,stroke:#333,stroke-width:2px;
    classDef action fill:#dcedc8,stroke:#333,stroke-width:2px;
    classDef button fill:#e1bee7,stroke:#333,stroke-width:2px;

    S((開始遊戲)) --> M[進入遊戲主畫面]
    M --> Click[點擊前進按鈕]
    Click --> EvDraw{隨機事件抽選}
    EvDraw --> EvNormal[普通事件]
    EvDraw --> EvBattle[戰鬥事件]
    EvDraw --> EvDialogue[對話事件]
    EvDraw --> EvCond[條件事件]
    EvNormal --> Process[處理事件結果（紀錄訊息）]
    EvBattle --> Process
    EvDialogue --> Process
    EvCond --> Process
    Process --> StoryCheck{檢查主線條件是否達成}
    StoryCheck -- 否 --> Click
    StoryCheck -- 是 --> Mainline[觸發主線劇情]
    Mainline --> EndingCheck{進入結局條件判定}
    EndingCheck -- 否 --> Click
    EndingCheck -- 是 --> Ending[進入結局劇情]
    Ending --> ReplayCheck{是否再次遊玩（可解鎖提示模式）}
    ReplayCheck -- 是 --> M
    ReplayCheck -- 否 --> E((結束遊戲))

    class S,E startEnd
    class M,Mainline,Ending mainNode
    class EvDraw,StoryCheck,EndingCheck,ReplayCheck decision
    class EvNormal,EvBattle,EvDialogue,EvCond,Process action
    class Click button
```

此流程圖以 Mermaid 繪製，描繪遊戲從起點(開始遊戲)到結局(結束遊戲)的主要循環與判定。

## 流程圖符號說明

- **startEnd**（灰色圓形）：起點與結束
- **mainNode**（藍色方框）：主流程或主線劇情
- **action**（淺綠方框）：一般操作或事件處理
- **decision**（黃色菱形）：條件判斷或流程分支
- **button**（淡紫方框）：玩家互動按鈕（例如「點擊前進按鈕」）

以上顏色與形狀對應於圖中的 `classDef` 設定，可協助快速辨識各節點類型。
