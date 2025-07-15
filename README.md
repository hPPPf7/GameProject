# GameProject

此專案為 2D 文字冒險遊戲。

## 產生文件

安裝 MkDocs 相關套件後，可使用下列指令產生網站：

```bash
pip install mkdocs mkdocs-material mkdocs-mermaid2-plugin pymdown-extensions
python scripts/generate_docs.py
mkdocs serve
```

產生的 Markdown 檔位於 `docs/` 目錄。

每次在 `data/story_data.json` 新增或修改事件後，都應執行 `python scripts/generate_docs.py`，以確保所有事件都寫入網站。產生的 `events.md` 會列出每個事件的選項與影響，方便直接在網站查看。
