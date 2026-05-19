import pygame
from settings import *


def _make_font(size):
    """Get a Chinese-capable font, falling back to default."""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    for path in candidates:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            continue
    return pygame.font.Font(None, size)


class UI:
    def __init__(self, screen):
        self.screen = screen
        self.font_small = _make_font(20)
        self.font_med = _make_font(36)
        self.font_large = _make_font(64)
        self.font_dmg = _make_font(24)
        self._title_glow = 0.0

    def _draw_panel(self, x, y, w, h, color=(15, 15, 25), border_color=None, alpha=0):
        """Draw a rounded-rect-style panel (simple rect with border accent)."""
        panel = pygame.Surface((w, h))
        panel.set_alpha(220)
        panel.fill(color)
        self.screen.blit(panel, (x, y))
        # Border
        border = border_color or MID_GRAY
        pygame.draw.rect(self.screen, border, (x, y, w, h), 1)
        # Subtle top accent line
        accent_color = (min(255, border[0] + 40),
                        min(255, border[1] + 40),
                        min(255, border[2] + 40))
        pygame.draw.line(self.screen, accent_color, (x + 8, y), (x + w - 8, y), 1)

    def draw_menu(self):
        self.screen.fill(BG_COLOR)

        # Decorative background lines
        for i in range(6):
            y = 100 + i * 80
            alpha = 40 - i * 5
            color = (30 + i * 5, 30 + i * 3, 50 + i * 3)
            pygame.draw.line(self.screen, color, (100, y), (SCREEN_WIDTH - 100, y), 1)

        # Title with glow pulse
        self._title_glow += 0.02
        glow = int(80 + 40 * abs((self._title_glow % 2.0) - 1.0))
        title = self.font_large.render("几何之刃", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        # Glow shadow
        glow_surf = self.font_large.render("几何之刃", True, (glow // 3, glow // 2, glow))
        self.screen.blit(glow_surf, (title_rect.x - 2, title_rect.y - 2))
        self.screen.blit(title, title_rect)

        # Title underline
        ul_y = title_rect.bottom + 8
        pygame.draw.line(self.screen, YELLOW,
                         (title_rect.left + 20, ul_y),
                         (title_rect.right - 20, ul_y), 2)

        # Subtitle
        sub = self.font_med.render("按 ENTER 开始游戏", True, (200, 200, 220))
        sub_rect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
        self.screen.blit(sub, sub_rect)

        # Controls panel
        controls = [
            ("A/D", "移动"),
            ("W/空格", "跳跃 · 二段跳"),
            ("J/Z", "攻击"),
            ("Q", "切换武器"),
            ("ESC/P", "暂停"),
        ]
        panel_w = 330
        panel_h = len(controls) * 28 + 20
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = SCREEN_HEIGHT // 2 + 55
        self._draw_panel(panel_x, panel_y, panel_w, panel_h,
                         color=(12, 12, 22), border_color=(50, 50, 70))

        y = panel_y + 12
        for key_text, desc in controls:
            key_surf = self.font_small.render(key_text, True, YELLOW)
            self.screen.blit(key_surf, (panel_x + 16, y))
            desc_surf = self.font_small.render(desc, True, MID_GRAY)
            self.screen.blit(desc_surf, (panel_x + 110, y))
            y += 28

    def draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(170)
        overlay.fill((5, 5, 12))
        self.screen.blit(overlay, (0, 0))

        # Panel
        pw, ph = 280, 100
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        self._draw_panel(px, py, pw, ph, color=(20, 20, 35), border_color=(80, 80, 100))
        txt = self.font_med.render("暂停", True, WHITE)
        r = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 18))
        self.screen.blit(txt, r)
        sub = self.font_small.render("按 ESC 或 P 继续", True, (160, 160, 180))
        sr = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 22))
        self.screen.blit(sub, sr)

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(190)
        overlay.fill((15, 5, 5))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 320, 110
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        self._draw_panel(px, py, pw, ph, color=(30, 8, 8), border_color=RED)
        txt = self.font_large.render("游戏结束", True, RED)
        r = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 22))
        self.screen.blit(txt, r)
        sub = self.font_small.render("按 ENTER 返回主菜单", True, (200, 160, 160))
        sr = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 28))
        self.screen.blit(sub, sr)

    def draw_victory(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(190)
        overlay.fill((5, 12, 5))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 320, 110
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        self._draw_panel(px, py, pw, ph, color=(8, 28, 8), border_color=GREEN)
        txt = self.font_large.render("胜利！", True, GREEN)
        r = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 22))
        self.screen.blit(txt, r)
        sub = self.font_small.render("按 ENTER 返回主菜单", True, (160, 200, 160))
        sr = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 28))
        self.screen.blit(sub, sr)

    def draw_boss_hp_bar(self, hp, max_hp):
        bar_w = 300
        bar_h = 18
        bar_x = SCREEN_WIDTH // 2 - bar_w // 2
        bar_y = 14

        # Outer panel
        pygame.draw.rect(self.screen, (15, 15, 25),
                         (bar_x - 6, bar_y - 6, bar_w + 12, bar_h + 12))
        pygame.draw.rect(self.screen, (50, 15, 15),
                         (bar_x - 6, bar_y - 6, bar_w + 12, bar_h + 12), 1)

        # Background
        pygame.draw.rect(self.screen, (30, 10, 10),
                         (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4))
        pygame.draw.rect(self.screen, (20, 20, 25),
                         (bar_x, bar_y, bar_w, bar_h))
        # Fill
        if hp > 0:
            ratio = hp / max_hp
            fill_w = int(bar_w * ratio)
            if ratio > 0.5:
                fill_color = GREEN
            elif ratio > 0.25:
                fill_color = YELLOW
            else:
                fill_color = RED
            pygame.draw.rect(self.screen, fill_color,
                             (bar_x, bar_y, fill_w, bar_h))
            # Shine line on top of fill
            shine_alpha = min(255, int(100 * ratio))
            shine_color = (shine_alpha, shine_alpha, shine_alpha)
            pygame.draw.line(self.screen, shine_color,
                             (bar_x + 2, bar_y + 2),
                             (bar_x + fill_w - 2, bar_y + 2), 1)
        # Border
        pygame.draw.rect(self.screen, RED,
                         (bar_x, bar_y, bar_w, bar_h), 1)
        # Label with background
        label = self.font_small.render("BOSS", True, WHITE)
        label_bg = pygame.Surface((label.get_width() + 8, label.get_height() + 4))
        label_bg.set_alpha(200)
        label_bg.fill((40, 8, 8))
        lx = bar_x - label.get_width() - 14
        ly = bar_y + bar_h // 2 - label.get_height() // 2 - 2
        self.screen.blit(label_bg, (lx - 4, ly - 2))
        self.screen.blit(label, (lx, ly))
        pygame.draw.rect(self.screen, RED,
                         (lx - 4, ly - 2, label.get_width() + 8, label.get_height() + 4), 1)
