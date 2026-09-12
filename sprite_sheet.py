"""Sprite-sheet data shared by the game and the desktop inspector.

Frame numbers in settings are one-based and follow row-major order.
Offsets are measured in source-image pixels, before game scaling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path

import pygame


def settings_path(image_path: Path) -> Path:
    return image_path.with_suffix(".animation.json")


@dataclass
class SheetSettings:
    columns: int = 3
    rows: int = 2
    fps: float = 10.0
    frame_order: list[int] = field(default_factory=list)
    offsets: dict[int, tuple[int, int]] = field(default_factory=dict)
    # Optional extraction rectangles for generated sheets with uneven spacing.
    frame_rects: list[tuple[int, int, int, int]] | None = None
    canvas_size: tuple[int, int] | None = None

    def validate(self) -> None:
        if any(type(value) is not int or value < 1 for value in (self.columns, self.rows)):
            raise ValueError("欄數與排數必須是正整數。")
        count = self.columns * self.rows
        if count > 256:
            raise ValueError("一次最多檢查 256 格。")
        if isinstance(self.fps, bool) or not isinstance(self.fps, (int, float)):
            raise ValueError("播放速度必須是數字。")
        if not math.isfinite(self.fps) or not 0.5 <= self.fps <= 60:
            raise ValueError("播放速度需介於 0.5 與 60 FPS。")
        if not self.frame_order:
            self.frame_order = list(range(1, count + 1))
        if any(type(number) is not int or not 1 <= number <= count for number in self.frame_order):
            raise ValueError(f"播放順序只能使用 1 到 {count} 的格號。")
        for number, offset in self.offsets.items():
            if type(number) is not int or not 1 <= number <= count:
                raise ValueError("偏移設定包含不存在的格號。")
            if len(offset) != 2 or any(type(value) is not int for value in offset):
                raise ValueError("每格偏移必須是兩個整數：X 與 Y。")
        if (self.frame_rects is None) != (self.canvas_size is None):
            raise ValueError("獨立取圖範圍與統一畫布尺寸必須一起設定。")
        if self.frame_rects is not None:
            if len(self.frame_rects) != count:
                raise ValueError("獨立取圖範圍的數量必須符合分格數。")
            if len(self.canvas_size) != 2 or any(type(v) is not int or v < 1 for v in self.canvas_size):
                raise ValueError("統一畫布尺寸必須是兩個正整數。")
            for rect in self.frame_rects:
                if len(rect) != 4 or any(type(v) is not int for v in rect):
                    raise ValueError("取圖範圍必須是四個整數：X、Y、寬、高。")
                x, y, w, h = rect
                if x < 0 or y < 0 or w < 1 or h < 1:
                    raise ValueError("取圖範圍的位置不能為負數，寬高必須大於零。")
                if w > self.canvas_size[0] or h > self.canvas_size[1]:
                    raise ValueError("統一畫布無法容納完整取圖範圍。")

    @classmethod
    def from_dict(cls, data: dict) -> SheetSettings:
        try:
            settings = cls(
                columns=data["columns"],
                rows=data["rows"],
                fps=data.get("fps", 10.0),
                frame_order=data.get("frame_order", []),
                offsets={int(key): tuple(value) for key, value in data.get("offsets", {}).items()},
                frame_rects=[tuple(rect) for rect in data["frame_rects"]] if data.get("frame_rects") is not None else None,
                canvas_size=tuple(data["canvas_size"]) if data.get("canvas_size") is not None else None,
            )
            settings.validate()
            return settings
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("動畫設定格式不正確。") from exc

    def to_dict(self) -> dict:
        self.validate()
        data = {
            "columns": self.columns,
            "rows": self.rows,
            "fps": self.fps,
            "frame_order": self.frame_order,
            "offsets": {str(key): list(value) for key, value in sorted(self.offsets.items())},
        }
        if self.frame_rects is not None:
            data["frame_rects"] = [list(rect) for rect in self.frame_rects]
            data["canvas_size"] = list(self.canvas_size)
        return data


class SpriteSheet:
    def __init__(self, path: Path, image: pygame.Surface, settings: SheetSettings):
        settings.validate()
        width, height = image.get_size()
        self.path = path
        self.image = image
        self.settings = settings
        if settings.frame_rects is not None:
            self.frame_size = settings.canvas_size
            self.raw_frames = []
            for rect in settings.frame_rects:
                if not image.get_rect().contains(pygame.Rect(rect)):
                    raise ValueError("取圖範圍超出原始圖片。")
                frame = pygame.Surface(self.frame_size, pygame.SRCALPHA)
                frame.blit(image, (0, 0), rect)
                self.raw_frames.append(frame)
            return
        if width % settings.columns or height % settings.rows:
            raise ValueError(f"圖片 {width} × {height} 無法平均切成 {settings.columns} 欄 × {settings.rows} 排。")
        self.frame_size = (width // settings.columns, height // settings.rows)
        frame_w, frame_h = self.frame_size
        if frame_w < 1 or frame_h < 1:
            raise ValueError("分格後的圖片尺寸不能為零。")
        self.raw_frames = [
            image.subsurface((col * frame_w, row * frame_h, frame_w, frame_h)).copy()
            for row in range(settings.rows)
            for col in range(settings.columns)
        ]

    @classmethod
    def load(cls, path: str | Path, *, columns: int = 3, rows: int = 2) -> SpriteSheet:
        image_path = Path(path).resolve()
        config_path = settings_path(image_path)
        settings = SheetSettings(columns=columns, rows=rows)
        if config_path.exists():
            try:
                settings = SheetSettings.from_dict(json.loads(config_path.read_text(encoding="utf-8")))
            except (OSError, ValueError) as exc:
                raise ValueError(f"無法讀取 {config_path.name}：{exc}") from exc
        return cls(image_path, pygame.image.load(str(image_path)), settings)

    def frame(self, number: int) -> pygame.Surface:
        if not 1 <= number <= len(self.raw_frames):
            raise ValueError("格號超出圖片範圍。")
        source = self.raw_frames[number - 1]
        offset = self.settings.offsets.get(number, (0, 0))
        if offset == (0, 0):
            return source
        frame = pygame.Surface(self.frame_size, pygame.SRCALPHA)
        frame.blit(source, offset)
        return frame

    def scaled_frames(self, target_height: int, *, smooth: bool = True) -> list[pygame.Surface]:
        width, height = self.frame_size
        size = (max(1, round(width * target_height / height)), target_height)
        scale = pygame.transform.smoothscale if smooth else pygame.transform.scale
        return [scale(self.frame(number), size) for number in self.settings.frame_order]

    def bounds(self, number: int) -> pygame.Rect:
        # Ignore nearly invisible generated background noise when measuring feet.
        return self.raw_frames[number - 1].get_bounding_rect(min_alpha=128)

    def clipped(self, number: int) -> bool:
        bounds = self.bounds(number).move(self.settings.offsets.get(number, (0, 0)))
        return bool(bounds.width and bounds.height and not pygame.Rect((0, 0), self.frame_size).contains(bounds))

    def align_feet(self, reference_number: int) -> None:
        reference = self.bounds(reference_number)
        if not reference.height:
            return
        ground = reference.bottom + self.settings.offsets.get(reference_number, (0, 0))[1]
        for number in range(1, len(self.raw_frames) + 1):
            bounds = self.bounds(number)
            if bounds.height:
                x, _ = self.settings.offsets.get(number, (0, 0))
                self.settings.offsets[number] = (x, ground - bounds.bottom)

    def save(self) -> Path:
        destination = settings_path(self.path)
        content = json.dumps(self.settings.to_dict(), ensure_ascii=False, indent=2) + "\n"
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination


@dataclass
class Playback:
    order: list[int]
    index: int = 0
    elapsed: float = 0.0

    @property
    def current(self) -> int:
        return self.order[self.index]

    def advance(self, dt: float, fps: float) -> bool:
        self.elapsed += max(0.0, dt)
        steps = int((self.elapsed + 1e-10) * fps)
        if steps:
            self.elapsed = max(0.0, self.elapsed - steps / fps)
            self.index = (self.index + steps) % len(self.order)
        return bool(steps)

    def step(self, direction: int) -> None:
        self.index = (self.index + direction) % len(self.order)
        self.elapsed = 0.0
