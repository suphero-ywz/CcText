import math
import pygame
from settings import *


ARROW_SPEED_X = 350
ARROW_SPEED_Y = -80
ARROW_GRAVITY = 600
ARROW_MAX_RANGE = 400


class Arrow:
    def __init__(self, x, y, facing, damage):
        self.x = float(x)
        self.y = float(y)
        self.vx = facing * ARROW_SPEED_X
        self.vy = ARROW_SPEED_Y
        self.damage = damage
        self.alive = True
        self.facing = facing
        self.start_x = x
        self.rect = pygame.Rect(int(x) - 2, int(y) - 2, 4, 4)

    def update(self, dt, level):
        if not self.alive:
            return
        self.vy += ARROW_GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Wall collision — kill arrow on solid tiles
        col = int(self.x) // TILE_SIZE
        row = int(self.y) // TILE_SIZE
        if 0 <= col < level.cols and 0 <= row < level.rows and level.is_solid(col, row):
            self.alive = False
            return

        # Range limit
        if abs(self.x - self.start_x) > ARROW_MAX_RANGE:
            self.alive = False
            return

        self.rect.center = (int(self.x), int(self.y))

    def render(self, screen, camera):
        if not self.alive:
            return
        sx = self.x - camera.offset_x
        sy = self.y - camera.offset_y

        # Out of screen
        if sx < -20 or sx > SCREEN_WIDTH + 20 or sy < -20 or sy > SCREEN_HEIGHT + 20:
            return

        # Arrow shaft
        angle = math.atan2(self.vy, self.vx)
        shaft_len = 14
        tip_x = sx + math.cos(angle) * shaft_len
        tip_y = sy + math.sin(angle) * shaft_len
        tail_x = sx - math.cos(angle) * shaft_len * 0.5
        tail_y = sy - math.sin(angle) * shaft_len * 0.5

        pygame.draw.line(screen, (60, 180, 60), (tail_x, tail_y), (tip_x, tip_y), 2)

        # Arrowhead (small V)
        head_angle1 = angle + math.radians(150)
        head_angle2 = angle - math.radians(150)
        head_len = 5
        pygame.draw.line(screen, (140, 255, 140),
                         (tip_x, tip_y),
                         (tip_x + math.cos(head_angle1) * head_len,
                          tip_y + math.sin(head_angle1) * head_len), 1)
        pygame.draw.line(screen, (140, 255, 140),
                         (tip_x, tip_y),
                         (tip_x + math.cos(head_angle2) * head_len,
                          tip_y + math.sin(head_angle2) * head_len), 1)
