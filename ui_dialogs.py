"""Small, temporary dialogs for save confirmation and inventory details."""
import pygame

from text_log import wrap_text
from ui_theme import draw_panel, TEXT, MUTED


def item_description(name, player):
    descriptions = {
        "奇怪的石頭": ("調查物品", "一塊仍在發熱的奇怪石頭。你已透過耳麥回報，暫時留在身邊觀察。",
                     "攜帶後，由相關劇情判斷後續反應。"),
        "草織護符": ("村民贈物", "村民悄悄塞給你的草編護符。他留下的提醒是：「記得別聽他們唱。」",
                   "留作調查紀念；目前沒有主動使用效果。"),
        "塗黑報告": ("調查線索", "上一任調查員留下的報告，多處內容被塗黑。",
                   "在相關劇情選項中調查或處理；攜帶時可能遇到後續線索。"),
    }
    category, description, usage = descriptions.get(
        name, ("隨身物品", "你在冒險途中取得的物品。", "請留意相關劇情選項，目前沒有主動使用效果。")
    )
    if name == "塗黑報告" and player.get("flags", {}).get("saw_redactions"):
        description += "你已辨認出「樣本#07」與「灰燼凹地」等關鍵字。"
    return category, description, usage


class GameDialog:
    def __init__(self):
        self.kind = None
        self.is_open = False
        self.item_names = []
        self.item_index = 0

    def confirm_new_game(self):
        self.kind = "new_game"
        self.is_open = True

    def inspect_item(self, player, index):
        items = list(player.get("inventory", []))
        if not 0 <= index < len(items):
            return False
        self.item_names = items
        self.item_index = index
        self.kind = "item"
        self.is_open = True
        return True

    def close(self):
        self.is_open = False

    def reset(self):
        self.__init__()

    def layout(self, screen_rect):
        modal = pygame.Rect(0, 0, 404, 356 if self.kind == "item" else 240)
        modal.center = screen_rect.center
        controls = {"modal": modal}
        if self.kind == "new_game":
            controls["cancel"] = pygame.Rect(modal.x + 28, modal.bottom - 62, 160, 36)
            controls["confirm"] = pygame.Rect(modal.right - 188, modal.bottom - 62, 160, 36)
        else:
            if len(self.item_names) > 1:
                controls["previous"] = pygame.Rect(modal.x + 24, modal.bottom - 100, 96, 32)
                controls["next"] = pygame.Rect(modal.right - 120, modal.bottom - 100, 96, 32)
            controls["close"] = pygame.Rect(modal.centerx - 80, modal.bottom - 54, 160, 32)
        return controls

    def handle_click(self, pos, screen_rect):
        controls = self.layout(screen_rect)
        for name, rect in controls.items():
            if name != "modal" and rect.collidepoint(pos):
                if name in {"cancel", "confirm", "close"}:
                    self.close()
                elif name == "previous":
                    self.item_index = (self.item_index - 1) % len(self.item_names)
                elif name == "next":
                    self.item_index = (self.item_index + 1) % len(self.item_names)
                return name
        if not controls["modal"].collidepoint(pos):
            self.close()
        return None

    def draw(self, destination, player, font, small_font, progress, draw_button):
        backdrop = pygame.Surface(destination.get_size(), pygame.SRCALPHA)
        backdrop.fill((5, 10, 16, round(150 * progress)))
        destination.blit(backdrop, (0, 0))
        surface = pygame.Surface(destination.get_size(), pygame.SRCALPHA)
        controls = self.layout(destination.get_rect())
        modal = controls["modal"]
        draw_panel(surface, modal)
        if self.kind == "new_game":
            title = "開始新的冒險？"
            paragraphs = ["目前的冒險進度將被取代。", "取消可保留目前存檔。"]
        else:
            title = self.item_names[self.item_index]
            category, description, usage = item_description(title, player)
            paragraphs = [category, description, usage]
        title_surface = font.render(title, True, TEXT)
        surface.blit(title_surface, title_surface.get_rect(midtop=(modal.centerx, modal.y + 22)))
        y = modal.y + 64
        for paragraph in paragraphs:
            for line in wrap_text(paragraph, small_font, modal.w - 48):
                surface.blit(small_font.render(line, True, TEXT), (modal.x + 24, y))
                y += 24
            y += 8
        labels = {"cancel": "取消", "confirm": "取代並開始", "previous": "上一件", "next": "下一件", "close": "關閉"}
        for name, rect in controls.items():
            if name != "modal":
                draw_button(surface, rect, labels[name], font=small_font, allow_hover=self.is_open)
        if self.kind == "item" and len(self.item_names) > 1:
            count = small_font.render(f"{self.item_index + 1} / {len(self.item_names)}", True, MUTED)
            surface.blit(count, count.get_rect(center=(modal.centerx, modal.bottom - 84)))
        surface.set_alpha(round(255 * progress))
        destination.blit(surface, (0, 0))
