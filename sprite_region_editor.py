"""Mouse editing of extraction rectangles; commits settings, never image pixels."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk, messagebox
import pygame
from sprite_sheet import SpriteSheet


class SpriteRegionEditor:
    def __init__(self, parent, sheet, selected, on_apply, make_photo):
        self.sheet = sheet
        self.selected = selected - 1
        self.on_apply = on_apply
        self.make_photo = make_photo
        w, h = sheet.frame_size
        self.original_rects = sheet.settings.frame_rects or [
            (col * w, row * h, w, h)
            for row in range(sheet.settings.rows) for col in range(sheet.settings.columns)
        ]
        self.rects = [pygame.Rect(r) for r in self.original_rects]
        self.drag = None
        self.window = tk.Toplevel(parent)
        self.window.transient(parent)
        self.window.title("調整各格取圖範圍")
        width = min(920, parent.winfo_screenwidth() - 100)
        height = min(820, parent.winfo_screenheight() - 120)
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(600, 500)
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)
        bar = ttk.Frame(self.window, padding=10)
        bar.grid(row=0, column=0, sticky="ew")
        self.number = tk.IntVar(value=selected)
        ttk.Label(bar, text="來源格").pack(side="left")
        spin = ttk.Spinbox(bar, from_=1, to=len(self.rects), width=4, textvariable=self.number, command=self.select)
        spin.pack(side="left", padx=8)
        spin.bind("<Return>", lambda event: self.select())
        ttk.Label(bar, text="拖曳框內移動；拖曳左上／右下角縮放；空白處拖曳重畫。").pack(side="left")
        self.canvas = tk.Canvas(self.window, background="#14202b", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.canvas.bind("<Button-1>", self.press)
        self.canvas.bind("<B1-Motion>", self.motion)
        self.canvas.bind("<ButtonRelease-1>", lambda event: setattr(self, "drag", None))
        footer = ttk.Frame(self.window, padding=10)
        footer.grid(row=2, column=0, sticky="ew")
        self.info = tk.StringVar()
        ttk.Label(footer, textvariable=self.info).pack(side="left")
        ttk.Button(footer, text="套用到預覽", command=self.apply).pack(side="right")
        ttk.Button(footer, text="取消", command=self.window.destroy).pack(side="right", padx=8)
        self.window.grab_set()

    def select(self):
        try:
            self.selected = max(0, min(len(self.rects) - 1, self.number.get() - 1))
        except tk.TclError:
            return
        self.number.set(self.selected + 1)
        self.draw()

    def draw(self):
        w, h = self.sheet.image.get_size()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.scale = min(cw / w, ch / h)
        size = (max(1, round(w * self.scale)), max(1, round(h * self.scale)))
        self.origin = ((cw - size[0]) // 2, (ch - size[1]) // 2)
        key = size
        if getattr(self, "photo_key", None) != key:
            base = pygame.Surface(size)
            base.fill((35, 45, 55))
            base.blit(pygame.transform.smoothscale(self.sheet.image, size), (0, 0))
            self.photo = self.make_photo(base)
            self.photo_key = key
        self.canvas.delete("all")
        self.canvas.create_image(*self.origin, image=self.photo, anchor="nw")
        ox, oy = self.origin
        for i, rect in enumerate(self.rects):
            x1, y1 = ox + rect.x * self.scale, oy + rect.y * self.scale
            x2, y2 = ox + rect.right * self.scale, oy + rect.bottom * self.scale
            color = "#8cf0cc" if i == self.selected else "#8091a2"
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color, width=2 if i == self.selected else 1)
            self.canvas.create_text(x1 + 10, y1 + 12, text=str(i + 1), fill=color)
            if i == self.selected:
                for x, y in ((x1, y1), (x2, y2)):
                    self.canvas.create_rectangle(x - 5, y - 5, x + 5, y + 5, fill=color)
        r = self.rects[self.selected]
        self.info.set(f"第 {self.selected + 1} 格：位置 {r.x}, {r.y} ／ 尺寸 {r.w} × {r.h}")

    def point(self, event):
        w, h = self.sheet.image.get_size()
        return (max(0, min(w, round((event.x - self.origin[0]) / self.scale))),
                max(0, min(h, round((event.y - self.origin[1]) / self.scale))))

    def press(self, event):
        point = self.point(event)
        rect = self.rects[self.selected]
        tolerance = 9 / self.scale
        near = lambda corner: abs(point[0] - corner[0]) < tolerance and abs(point[1] - corner[1]) < tolerance
        if near(rect.topleft):
            mode = "top"
        elif near(rect.bottomright):
            mode = "bottom"
        elif rect.collidepoint(point):
            mode = "move"
        else:
            mode = "new"
        self.drag = mode, point, rect.copy()

    def motion(self, event):
        if self.drag is None:
            return
        mode, start, original = self.drag
        x, y = self.point(event)
        if mode == "move":
            rect = original.move(x - start[0], y - start[1]).clamp(self.sheet.image.get_rect())
        else:
            fixed = original.bottomright if mode == "top" else original.topleft if mode == "bottom" else start
            rect = pygame.Rect(min(x, fixed[0]), min(y, fixed[1]), max(1, abs(x - fixed[0])), max(1, abs(y - fixed[1])))
            rect.clamp_ip(self.sheet.image.get_rect())
        self.rects[self.selected] = rect
        self.draw()

    def apply(self):
        settings = deepcopy(self.sheet.settings)
        settings.canvas_size = self.sheet.frame_size
        settings.frame_rects = [tuple(rect) for rect in self.rects]
        for number, (old, new) in enumerate(zip(self.original_rects, self.rects), 1):
            x, y = settings.offsets.get(number, (0, 0))
            settings.offsets[number] = (x + new.x - old[0], y + new.y - old[1])
        try:
            sheet = SpriteSheet(self.sheet.path, self.sheet.image, settings)
        except ValueError as exc:
            messagebox.showerror("無法套用取圖範圍", str(exc), parent=self.window)
            return
        self.on_apply(sheet)
        self.window.destroy()
