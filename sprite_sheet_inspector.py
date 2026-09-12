"""Desktop sprite-sheet inspector. Run with the project's Python environment."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from sprite_sheet import Playback, SheetSettings, SpriteSheet
from animation_preview import AnimationSequencePreview
from sprite_region_editor import SpriteRegionEditor


ROOT = Path(__file__).resolve().parent
DEFAULT_SHEET = ROOT / "assets" / "sprite_sheet" / "player_walk.png"
BG = "#101923"
PANEL = "#192634"
TEXT = "#e3ebf1"
MUTED = "#a6b7c8"
ACCENT = "#7ce0c4"


def photo_image(surface: pygame.Surface) -> tk.PhotoImage:
    width, height = surface.get_size()
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    return tk.PhotoImage(data=header + pygame.image.tobytes(surface, "RGB"), format="PPM")


class SpriteSheetInspector:
    def __init__(self, root: tk.Tk, image_path: Path = DEFAULT_SHEET):
        self.root = root
        self.sheet: SpriteSheet | None = None
        self.playback = Playback([1])
        self.selected = 1
        self.playing = True
        self.dirty = False
        self.last_time = time.perf_counter()
        self.travel = 0.0
        self.preview_photo = None
        self.preview_surface = None
        self.thumbnails: list[tk.PhotoImage] = []
        self.thumbnail_items: dict[int, int] = {}
        self.scroll_canvases: list[tk.Canvas] = []
        self.scaled_cache: dict[tuple, pygame.Surface] = {}
        self.background_cache = None
        self.after_id = None
        self.closed = False

        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="開啟圖片後即可開始檢查。")
        self.frame_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.play_var = tk.StringVar(value="暫停")
        self.fps_var = tk.DoubleVar(value=10)
        self.zoom_var = tk.StringVar(value="3")
        self.background_var = tk.StringVar(value="棋盤格")
        self.guides_var = tk.BooleanVar(value=True)
        self.onion_var = tk.BooleanVar(value=False)
        self.smooth_var = tk.BooleanVar(value=True)
        self.compare_var = tk.BooleanVar(value=False)
        self.sequence_var = tk.BooleanVar(value=False)
        self.sequence_previews = None
        self.moving_var = tk.BooleanVar(value=False)
        self.speed_var = tk.DoubleVar(value=120)
        self.travel_summary_var = tk.StringVar(value="位移速度：120 遊戲像素／秒")
        self.columns_var = tk.IntVar(value=3)
        self.rows_var = tk.IntVar(value=2)
        self.order_var = tk.StringVar(value="1, 2, 3, 4, 5, 6")
        self.offset_x_var = tk.IntVar(value=0)
        self.offset_y_var = tk.IntVar(value=0)

        root.title("Sprite Sheet 檢查工具 — 菜鳥調查隊日誌")
        root.configure(background=BG)
        width = min(1240, root.winfo_screenwidth() - 80)
        height = min(840, root.winfo_screenheight() - 100)
        root.geometry(f"{width}x{height}")
        root.minsize(960, 680)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._style()
        self._build_ui()
        root.bind("<space>", lambda event: self._shortcut(event, self.toggle_play))
        root.bind("<Left>", lambda event: self._shortcut(event, lambda: self.step(-1)))
        root.bind("<Right>", lambda event: self._shortcut(event, lambda: self.step(1)))
        root.bind("<Control-o>", lambda event: self.open_file())
        root.bind("<Control-s>", lambda event: self.save())
        root.bind("<MouseWheel>", self._scroll_controls)
        self.load(image_path)
        self.after_id = root.after(20, self._tick)

    def _style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Microsoft JhengHei UI", 10), background=PANEL, foreground=TEXT)
        style.configure("TFrame", background=PANEL)
        style.configure("TLabel", background=PANEL, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Title.TLabel", font=("Microsoft JhengHei UI", 16, "bold"), foreground=ACCENT)
        style.configure("TButton", padding=(9, 7), background="#283c4f", borderwidth=0)
        style.map("TButton", background=[("active", "#36556b")])
        style.configure("Accent.TButton", foreground=BG, background=ACCENT)
        style.map("Accent.TButton", background=[("active", "#a1f2dc")])
        style.configure("TCheckbutton", background=PANEL)
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.configure("TEntry", fieldbackground="#101d29", insertcolor=TEXT, padding=5)
        style.configure("TSpinbox", fieldbackground="#101d29", arrowsize=16, padding=4)
        style.configure("TCombobox", fieldbackground="#101d29", padding=4)
        style.map("TCombobox", fieldbackground=[("readonly", "#101d29")], foreground=[("readonly", TEXT)])
        style.configure("TNotebook", background=PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(16, 9), background="#243548")
        style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
        style.configure("Horizontal.TScale", background=PANEL, troughcolor="#0d1822")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = ttk.Frame(self.root, padding=(18, 12))
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="SPRITE SHEET  檢查工具", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.path_var, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Button(header, text="開啟圖片…", command=self.open_file).grid(row=0, column=1, rowspan=2, padx=(12, 6))
        ttk.Button(header, text="重新載入", command=self.reload).grid(row=0, column=2, rowspan=2)

        body = ttk.Frame(self.root, padding=12)
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        sidebar = ttk.Frame(body, width=288)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 16))
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(sidebar)
        notebook.grid(row=0, column=0, sticky="nsew")
        playback_tab = self._scrollable_tab(notebook, "播放檢查")
        editing_tab = self._scrollable_tab(notebook, "切圖與校正")
        notebook.bind("<<NotebookTabChanged>>", lambda event: self._pause_for_editing(notebook))
        self._playback_controls(playback_tab)
        self._editing_controls(editing_tab)
        for tab in (playback_tab, editing_tab):
            for widget in tab.winfo_children():
                if isinstance(widget, ttk.Label):
                    widget.configure(wraplength=300)
        ttk.Button(sidebar, text="儲存動畫設定", style="Accent.TButton", command=self.save).grid(row=1, column=0, sticky="ew", pady=(14, 5))
        ttk.Label(sidebar, text="儲存後，重新啟動遊戲套用。\n縮放、疊影與預覽位移不會存入遊戲。", style="Muted.TLabel").grid(row=2, column=0, sticky="w")

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        ttk.Label(right, textvariable=self.frame_var, foreground=ACCENT).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.canvas = tk.Canvas(right, background=BG, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.preview_item = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Configure>", lambda event: self.draw_preview())
        ttk.Label(right, text="所有來源格  ·  點選可暫停檢查；左右方向鍵依播放順序切換", style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(12, 6))
        self.timeline = tk.Canvas(right, height=118, background=BG, highlightthickness=0)
        self.timeline.grid(row=3, column=0, sticky="ew")
        scrollbar = ttk.Scrollbar(right, orient="horizontal", command=self.timeline.xview)
        scrollbar.grid(row=4, column=0, sticky="ew")
        self.timeline.configure(xscrollcommand=scrollbar.set)
        self.timeline.bind("<Button-1>", self._thumbnail_click)
        ttk.Label(self.root, textvariable=self.status_var, padding=(18, 8), style="Muted.TLabel", anchor="w").grid(row=2, column=0, sticky="ew")

    def _scrollable_tab(self, notebook, title):
        container = ttk.Frame(notebook)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        canvas = tk.Canvas(container, background=PANEL, width=324, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)
        content = ttk.Frame(canvas, padding=(10, 14))
        window = canvas.create_window(0, 0, anchor="nw", window=content)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
        content.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        self.scroll_canvases.append(canvas)
        notebook.add(container, text=title)
        return content

    def _scroll_controls(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if widget in self.scroll_canvases:
                if widget.yview() != (0.0, 1.0):
                    widget.yview_scroll(-1 if event.delta > 0 else 1, "units")
                return "break"
            widget = widget.master

    def _playback_controls(self, parent):
        buttons = ttk.Frame(parent)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="◀ 前格", command=lambda: self.step(-1)).pack(side="left")
        ttk.Button(buttons, textvariable=self.play_var, command=self.toggle_play).pack(side="left", expand=True, fill="x", padx=5)
        ttk.Button(buttons, text="後格 ▶", command=lambda: self.step(1)).pack(side="left")
        ttk.Label(parent, text="播放速度（FPS）").pack(anchor="w", pady=(20, 4))
        fps_row = ttk.Frame(parent)
        fps_row.pack(fill="x")
        ttk.Scale(fps_row, from_=0.5, to=30, variable=self.fps_var, command=self._speed_changed).pack(side="left", fill="x", expand=True)
        fps_spin = ttk.Spinbox(fps_row, from_=0.5, to=60, increment=0.5, width=5, textvariable=self.fps_var, command=self._speed_changed)
        fps_spin.pack(side="right", padx=(8, 0))
        fps_spin.bind("<Return>", self._speed_changed)
        fps_spin.bind("<FocusOut>", self._speed_changed)
        presets = ttk.Frame(parent)
        presets.pack(fill="x", pady=(7, 4))
        for fps in (2, 6, 10, 15):
            ttk.Button(presets, text=f"{fps}", width=4, command=lambda value=fps: self.set_fps(value)).pack(side="left", expand=True, fill="x", padx=2)
        ttk.Label(parent, textvariable=self.summary_var, style="Muted.TLabel").pack(anchor="w", pady=(3, 14))
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Label(row, text="縮放").pack(side="left")
        zoom = ttk.Combobox(row, textvariable=self.zoom_var, values=("1", "2", "3", "4", "5"), state="readonly", width=5)
        zoom.pack(side="right")
        zoom.bind("<<ComboboxSelected>>", lambda event: self.refresh_preview())
        ttk.Label(parent, text="1 倍 = 遊戲中的 96 像素畫布高度", style="Muted.TLabel").pack(anchor="w", pady=(5, 12))
        ttk.Checkbutton(parent, text="連續動作：待機 → 接近 → 攻擊 → 返回", variable=self.sequence_var, command=self.refresh_preview).pack(anchor="w", pady=3)
        ttk.Checkbutton(parent, text="並排比較：平滑／清晰", variable=self.compare_var, command=self.refresh_preview).pack(anchor="w", pady=3)
        ttk.Label(parent, text="連續預覽沿用遊戲角色，走路／攻擊圖的未儲存調整也會套用。", style="Muted.TLabel").pack(anchor="w", pady=5)
        for label, variable in (("中心線、腳底線與外框", self.guides_var), ("疊上前一格（半透明）", self.onion_var), ("平滑縮放（與遊戲相同）", self.smooth_var)):
            ttk.Checkbutton(parent, text=label, variable=variable, command=self.refresh_preview).pack(anchor="w", pady=3)
        ttk.Label(parent, text="背景").pack(anchor="w", pady=(14, 4))
        background = ttk.Combobox(parent, textvariable=self.background_var, values=("棋盤格", "深色", "淺色", "草綠色"), state="readonly")
        background.pack(fill="x")
        background.bind("<<ComboboxSelected>>", lambda event: self.refresh_preview())
        ttk.Checkbutton(parent, text="橫向移動預覽", variable=self.moving_var, command=self.refresh_preview).pack(anchor="w", pady=(16, 3))
        ttk.Label(parent, textvariable=self.travel_summary_var, style="Muted.TLabel").pack(anchor="w")
        ttk.Scale(parent, from_=0, to=300, variable=self.speed_var, command=lambda value: self.travel_summary_var.set(f"位移速度：{float(value):.0f} 遊戲像素／秒")).pack(fill="x", pady=5)
        ttk.Label(parent, text="空白鍵：播放／暫停\n← →：逐格查看\nCtrl+O：開啟　Ctrl+S：儲存", style="Muted.TLabel").pack(anchor="w", pady=(16, 0))

    def _editing_controls(self, parent):
        ttk.Button(parent, text="拖拉調整各格取圖範圍…", command=self.edit_regions).pack(fill="x", pady=(0, 12))
        ttk.Label(parent, text="規則分格").pack(anchor="w")
        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=(7, 10))
        ttk.Label(grid, text="欄數").pack(side="left")
        ttk.Spinbox(grid, from_=1, to=64, width=4, textvariable=self.columns_var).pack(side="left", padx=(5, 16))
        ttk.Label(grid, text="排數").pack(side="left")
        ttk.Spinbox(grid, from_=1, to=64, width=4, textvariable=self.rows_var).pack(side="left", padx=5)
        ttk.Button(parent, text="套用分格", command=self.apply_grid).pack(fill="x")
        ttk.Label(parent, text="套用分格會恢復等分，並重設播放順序與偏移。", style="Muted.TLabel").pack(anchor="w", pady=(5, 18))
        ttk.Label(parent, text="播放順序（來源格號）").pack(anchor="w")
        order_entry = ttk.Entry(parent, textvariable=self.order_var)
        order_entry.pack(fill="x", pady=7)
        order_entry.bind("<Return>", lambda event: self.apply_order())
        ttk.Button(parent, text="套用順序", command=self.apply_order).pack(fill="x")
        ttk.Label(parent, text="例如 1,2,3,4,5,6；可省略或重複格號。\n原圖排列：上排左到右，再往下一排。", style="Muted.TLabel").pack(anchor="w", pady=(5, 18))
        ttk.Label(parent, text="目前來源格的位置偏移").pack(anchor="w")
        offsets = ttk.Frame(parent)
        offsets.pack(fill="x", pady=7)
        for label, variable in (("X", self.offset_x_var), ("Y", self.offset_y_var)):
            ttk.Label(offsets, text=label).pack(side="left", padx=(0, 5))
            spin = ttk.Spinbox(offsets, from_=-8192, to=8192, width=6, textvariable=variable, command=self.apply_offset)
            spin.pack(side="left", padx=(0, 12))
            spin.bind("<Return>", lambda event: self.apply_offset())
        ttk.Label(parent, text="單位：原圖像素。X 正值向右，Y 正值向下。", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(parent, text="套用目前格偏移", command=self.apply_offset).pack(fill="x", pady=(8, 5))
        ttk.Button(parent, text="重設目前格偏移", command=self.reset_offset).pack(fill="x", pady=5)
        ttk.Button(parent, text="全部腳底對齊目前格", command=self.align_feet).pack(fill="x", pady=5)
        ttk.Label(parent, text="腳底線固定參考第 1 格。\n黃色框是目前角色輪廓，紅框表示裁切。\n對齊位置不能補出缺少的走路動作。", style="Muted.TLabel").pack(anchor="w", pady=(14, 0))

    def _shortcut(self, event, callback):
        if isinstance(event.widget, (ttk.Entry, ttk.Spinbox, ttk.Combobox, tk.Entry)):
            return None
        callback()
        return "break"

    def _pause_for_editing(self, notebook):
        if notebook.index("current") == 1:
            self.playing = False
            self.play_var.set("播放")

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        choice = messagebox.askyesnocancel("尚未儲存", "要儲存目前的動畫設定嗎？", parent=self.root)
        if choice is None:
            return False
        return self.save() if choice else True

    def open_file(self):
        if not self._confirm_discard():
            return
        filename = filedialog.askopenfilename(parent=self.root, title="開啟 Sprite Sheet", initialdir=str(self.sheet.path.parent if self.sheet else ROOT / "assets"), filetypes=[("圖片", "*.png *.webp *.jpg *.jpeg *.bmp"), ("所有檔案", "*.*")])
        if filename:
            self.load(Path(filename), columns=1, rows=1)

    def reload(self):
        if self.sheet and self._confirm_discard():
            self.load(self.sheet.path, columns=self.sheet.settings.columns, rows=self.sheet.settings.rows)

    def load(self, path: Path, *, columns: int = 3, rows: int = 2):
        try:
            sheet = SpriteSheet.load(path, columns=columns, rows=rows)
        except (OSError, ValueError, pygame.error) as exc:
            messagebox.showerror("無法載入圖片", str(exc), parent=self.root)
            return False
        self.sheet = sheet
        self.sequence_previews = None
        self.selected = 1
        self.playback = Playback(sheet.settings.frame_order.copy())
        self.selected = self.playback.current
        self.columns_var.set(sheet.settings.columns)
        self.rows_var.set(sheet.settings.rows)
        self.fps_var.set(sheet.settings.fps)
        self.order_var.set(", ".join(map(str, sheet.settings.frame_order)))
        self.path_var.set(f"{sheet.path.name}  ·  {sheet.image.get_width()} × {sheet.image.get_height()}")
        self.dirty = False
        self.travel = 0
        self.last_time = time.perf_counter()
        self.scaled_cache.clear()
        self._build_thumbnails()
        self._sync_frame()
        self.status_var.set("已載入。先用 2 FPS 與前格疊影檢查腳步、角色中心和首尾銜接。")
        return True

    def toggle_play(self):
        self.playing = not self.playing
        self.play_var.set("暫停" if self.playing else "播放")
        if self.playing:
            self.selected = self.playback.current
            self._sync_frame()
        self.last_time = time.perf_counter()

    def step(self, direction: int):
        if not self.sheet:
            return
        self.sequence_var.set(False)
        self.playing = False
        self.play_var.set("播放")
        self.playback.step(direction)
        self.selected = self.playback.current
        self._sync_frame()

    def select_frame(self, number: int):
        self.sequence_var.set(False)
        self.playing = False
        self.play_var.set("播放")
        self.selected = number
        if number in self.playback.order:
            self.playback.index = self.playback.order.index(number)
        self.playback.elapsed = 0
        self._sync_frame()

    def set_fps(self, value: float):
        self.fps_var.set(value)
        self._speed_changed()

    def _speed_changed(self, *_):
        if not self.sheet:
            return
        try:
            fps = round(float(self.fps_var.get()) * 2) / 2
            if not math.isfinite(fps) or not 0.5 <= fps <= 60:
                raise ValueError
        except (ValueError, OverflowError, tk.TclError):
            self.status_var.set("播放速度請輸入 0.5 到 60 FPS。")
            return
        if fps != self.sheet.settings.fps:
            self.sheet.settings.fps = fps
            self.playback.elapsed = 0
            self._mark_dirty()
        self.fps_var.set(fps)
        self._summary()

    def apply_grid(self):
        if not self.sheet:
            return
        if self.sheet.settings.frame_rects and not messagebox.askyesno(
            "改成等分取圖？", "這會清除目前逐格校正的取圖範圍、順序與偏移。確定要恢復等分嗎？", parent=self.root
        ):
            return
        try:
            settings = SheetSettings(columns=self.columns_var.get(), rows=self.rows_var.get(), fps=self.sheet.settings.fps)
            sheet = SpriteSheet(self.sheet.path, self.sheet.image, settings)
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("無法套用分格", str(exc), parent=self.root)
            return
        self.sheet = sheet
        self.playback = Playback(settings.frame_order.copy())
        self.selected = 1
        self.order_var.set(", ".join(map(str, settings.frame_order)))
        self.scaled_cache.clear()
        self._build_thumbnails()
        self._mark_dirty()
        self._sync_frame()

    def apply_order(self):
        if not self.sheet:
            return
        try:
            order = [int(value.strip()) for value in self.order_var.get().replace("，", ",").split(",")]
            if not order or any(not 1 <= number <= len(self.sheet.raw_frames) for number in order):
                raise ValueError
        except ValueError:
            messagebox.showerror("播放順序不正確", f"請用逗號分隔 1 到 {len(self.sheet.raw_frames)} 的格號。", parent=self.root)
            return
        self.sheet.settings.frame_order = order
        self.playback = Playback(order.copy())
        self.selected = self.playback.current
        self._mark_dirty()
        self._sync_frame()

    def apply_offset(self):
        if not self.sheet:
            return
        try:
            offset = (self.offset_x_var.get(), self.offset_y_var.get())
        except tk.TclError:
            self.status_var.set("位置偏移請輸入整數。")
            return
        self.sheet.settings.offsets[self.selected] = offset
        self.scaled_cache.clear()
        self._mark_dirty()
        self._sync_frame()

    def reset_offset(self):
        self.offset_x_var.set(0)
        self.offset_y_var.set(0)
        self.apply_offset()

    def align_feet(self):
        if self.sheet:
            self.sheet.align_feet(self.selected)
            self.scaled_cache.clear()
            self._mark_dirty()
            self._sync_frame()

    def _mark_dirty(self):
        self.sequence_previews = None
        self.dirty = True
        self.status_var.set("有未儲存的調整。按「儲存動畫設定」後，重新啟動遊戲套用。")

    def save(self) -> bool:
        if not self.sheet:
            return False
        if any(self.sheet.clipped(number) for number in range(1, len(self.sheet.raw_frames) + 1)):
            messagebox.showerror("偏移造成裁切", "有角色輪廓超出格子，請先調整偏移，避免把裁切結果套用到遊戲。", parent=self.root)
            return False
        try:
            path = self.sheet.save()
        except (OSError, ValueError) as exc:
            messagebox.showerror("儲存失敗", str(exc), parent=self.root)
            return False
        self.dirty = False
        self.status_var.set(f"已儲存 {path.name}。角色原圖沒有改動；重新啟動遊戲即可套用。")
        return True

    def _summary(self):
        if self.sheet:
            fps = self.sheet.settings.fps
            count = len(self.playback.order)
            self.summary_var.set(f"每格 {1000 / fps:.0f} ms  ·  循環 {count / fps:.2f} 秒")

    def _sync_frame(self):
        if not self.sheet:
            return
        x, y = self.sheet.settings.offsets.get(self.selected, (0, 0))
        self.offset_x_var.set(x)
        self.offset_y_var.set(y)
        w, h = self.sheet.frame_size
        sequence = f"播放第 {self.playback.index + 1} / {len(self.playback.order)} 格" if self.selected in self.playback.order else "此格未加入播放順序"
        clipped = "  ·  偏移造成裁切" if self.sheet.clipped(self.selected) else ""
        self.frame_var.set(f"來源格 {self.selected}  ·  {sequence}  ·  單格 {w} × {h}{clipped}")
        for number, item in self.thumbnail_items.items():
            self.timeline.itemconfigure(item, outline=ACCENT if number == self.selected else "#2b3d4d", width=3 if number == self.selected else 1)
        self._summary()
        self.draw_preview()

    def refresh_preview(self):
        self.scaled_cache.clear()
        self.background_cache = None
        self.draw_preview()

    def _build_thumbnails(self):
        self.timeline.delete("all")
        self.thumbnail_items.clear()
        self.thumbnails.clear()
        if not self.sheet:
            return
        for index, frame in enumerate(self.sheet.raw_frames):
            width, height = frame.get_size()
            ratio = min(76 / width, 76 / height)
            thumbnail = pygame.Surface((88, 88))
            thumbnail.fill((33, 47, 59))
            scaled = pygame.transform.smoothscale(frame, (max(1, round(width * ratio)), max(1, round(height * ratio))))
            thumbnail.blit(scaled, scaled.get_rect(center=(44, 44)))
            photo = photo_image(thumbnail)
            self.thumbnails.append(photo)
            x = 6 + index * 100
            self.timeline.create_image(x + 3, 5, image=photo, anchor="nw")
            self.thumbnail_items[index + 1] = self.timeline.create_rectangle(x, 2, x + 94, 114, outline="#2b3d4d")
            self.timeline.create_text(x + 47, 103, text=f"格 {index + 1}", fill=TEXT, font=("Microsoft JhengHei UI", 9))
        self.timeline.configure(scrollregion=(0, 0, len(self.thumbnails) * 100 + 12, 118))

    def _thumbnail_click(self, event):
        if self.sheet:
            number = int((self.timeline.canvasx(event.x) - 6) // 100) + 1
            if 1 <= number <= len(self.sheet.raw_frames):
                self.select_frame(number)

    def _background(self, size: tuple[int, int]) -> pygame.Surface:
        key = (size, self.background_var.get())
        if self.background_cache and self.background_cache[0] == key:
            return self.background_cache[1].copy()
        surface = pygame.Surface(size)
        colors = {"深色": (18, 26, 36), "淺色": (225, 230, 233), "草綠色": (97, 126, 89)}
        surface.fill(colors.get(key[1], (28, 39, 51)))
        if key[1] == "棋盤格":
            for row in range(0, size[1], 24):
                for col in range(0, size[0], 24):
                    if (row // 24 + col // 24) % 2:
                        pygame.draw.rect(surface, (34, 47, 60), (col, row, 24, 24))
        self.background_cache = (key, surface.copy())
        return surface

    def _scaled(self, number: int, size: tuple[int, int], smooth=None) -> pygame.Surface:
        smooth = self.smooth_var.get() if smooth is None else smooth
        key = (number, size, smooth)
        if key not in self.scaled_cache:
            source = self.sheet.frame(number)
            # Match the game at 96 px first; enlarge that view for inspection.
            w, h = self.sheet.frame_size
            game_size = (max(1, round(w * 96 / h)), 96)
            if smooth:
                game_frame = pygame.transform.smoothscale(source, game_size)
            else:
                game_frame = pygame.transform.scale(source, game_size)
            self.scaled_cache[key] = pygame.transform.scale(game_frame, size)
        return self.scaled_cache[key]

    def edit_regions(self):
        if self.sheet:
            self.playing = False
            self.play_var.set("播放")
            self.region_editor = SpriteRegionEditor(self.root, self.sheet, self.selected, self._apply_regions, photo_image)

    def _apply_regions(self, sheet):
        self.sheet = sheet
        self.scaled_cache.clear()
        self._build_thumbnails()
        self._mark_dirty()
        self._sync_frame()

    def _sequences(self):
        if self.sequence_previews is None:
            self.sequence_previews = {
                smooth: AnimationSequencePreview(self.sheet, smooth=smooth) for smooth in (True, False)
            }
        return self.sequence_previews

    def _draw_extended_preview(self, surface):
        pygame.font.init()
        if not hasattr(self, "preview_font"):
            self.preview_font = pygame.font.Font(str(ROOT / "assets" / "Cubic_11.ttf"), 16)
        w, h = surface.get_size()
        modes = (True, False) if self.compare_var.get() else (self.smooth_var.get(),)
        panel_w = w / len(modes)
        for i, smooth in enumerate(modes):
            if self.sequence_var.get():
                preview = self._sequences()[smooth]
                source = preview.render(self.preview_font)
                scale = min((panel_w - 20) / source.get_width(), (h - 45) / source.get_height(), float(self.zoom_var.get()))
                size = (max(1, round(source.get_width() * scale)), max(1, round(source.get_height() * scale)))
                frame = pygame.transform.scale(source, size)
                self.frame_var.set(f"連續動作：{preview.label} ／ 使用遊戲的移動速度與後退播放")
            else:
                sw, sh = self.sheet.frame_size
                scale = min(96 * float(self.zoom_var.get()) / sh, (panel_w - 24) / sw, (h - 60) / sh)
                size = (max(1, round(sw * scale)), max(1, round(sh * scale)))
                frame = self._scaled(self.selected, size, smooth)
            rect = frame.get_rect(center=(round(panel_w * (i + .5)), h // 2 + 10))
            surface.blit(frame, rect)
            label = self.preview_font.render("平滑" if smooth else "清晰", True, (220, 235, 240))
            surface.blit(label, label.get_rect(midtop=(round(panel_w * (i + .5)), 10)))
        if len(modes) == 2:
            pygame.draw.line(surface, (80, 105, 125), (w // 2, 0), (w // 2, h))

    def _show_surface(self, surface):
        self.preview_surface = surface
        self.preview_photo = photo_image(surface)
        self.canvas.itemconfigure(self.preview_item, image=self.preview_photo)

    def draw_preview(self):
        if not self.sheet or not hasattr(self, "canvas") or self.closed:
            return
        size = (max(2, self.canvas.winfo_width()), max(2, self.canvas.winfo_height()))
        if min(size) <= 2:
            return
        surface = self._background(size)
        if self.compare_var.get() or self.sequence_var.get():
            self._draw_extended_preview(surface)
            self._show_surface(surface)
            return
        zoom = float(self.zoom_var.get())
        source_w, source_h = self.sheet.frame_size
        scale = min(96 * zoom / source_h, (size[0] - 40) / source_w, (size[1] - 50) / source_h)
        frame_size = (max(1, round(source_w * scale)), max(1, round(source_h * scale)))
        x = (size[0] - frame_size[0]) // 2
        if self.moving_var.get():
            distance = max(1, size[0] - frame_size[0] - 32)
            x = 16 + round(self.travel % distance)
        y = (size[1] - frame_size[1]) // 2
        origin = (x, y)
        if self.onion_var.get():
            previous = self.playback.order[(self.playback.index - 1) % len(self.playback.order)]
            ghost = self._scaled(previous, frame_size).copy()
            ghost.fill((115, 230, 230, 255), special_flags=pygame.BLEND_RGBA_MULT)
            ghost.set_alpha(100)
            surface.blit(ghost, origin)
        surface.blit(self._scaled(self.selected, frame_size), origin)
        if self.guides_var.get():
            frame_rect = pygame.Rect(origin, frame_size)
            pygame.draw.rect(surface, (91, 116, 136), frame_rect, 1)
            reference = self.sheet.bounds(1).move(self.sheet.settings.offsets.get(1, (0, 0)))
            ground = y + round(reference.bottom * scale)
            pygame.draw.line(surface, (124, 224, 196), (0, ground), (size[0], ground))
            pygame.draw.line(surface, (76, 109, 131), (frame_rect.centerx, 0), (frame_rect.centerx, size[1]))
            bounds = self.sheet.bounds(self.selected).move(self.sheet.settings.offsets.get(self.selected, (0, 0)))
            outline = pygame.Rect(x + round(bounds.x * scale), y + round(bounds.y * scale), max(1, round(bounds.width * scale)), max(1, round(bounds.height * scale)))
            color = (255, 110, 110) if self.sheet.clipped(self.selected) else (225, 192, 113)
            pygame.draw.rect(surface, color, outline, 1)
        self._show_surface(surface)

    def _tick(self):
        if self.closed:
            return
        now = time.perf_counter()
        dt = now - self.last_time
        self.last_time = now
        if self.playing and self.sheet and self.sequence_var.get():
            for preview in self._sequences().values():
                preview.update(dt)
            self.draw_preview()
        elif self.playing and self.sheet:
            changed = self.playback.advance(dt, self.sheet.settings.fps)
            if self.moving_var.get():
                self.travel += self.speed_var.get() * float(self.zoom_var.get()) * dt
            if changed:
                self.selected = self.playback.current
                self._sync_frame()
            elif self.moving_var.get():
                self.draw_preview()
        self.after_id = self.root.after(20, self._tick)

    def close(self):
        if not self._confirm_discard():
            return
        self.closed = True
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Sprite Sheet 檢查工具")
    parser.add_argument("image", nargs="?", type=Path, default=DEFAULT_SHEET, help="要檢查的圖片；預設為玩家走路圖")
    args = parser.parse_args()
    root = tk.Tk()
    SpriteSheetInspector(root, args.image)
    root.mainloop()


if __name__ == "__main__":
    main()
