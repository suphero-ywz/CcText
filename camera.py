import random
from settings import *


class Camera:
    def __init__(self, width, height, level_width, level_height):
        self.width = width
        self.height = height
        self.level_width = level_width
        self.level_height = level_height
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.shake_intensity = 0
        self.shake_duration = 0.0
        self.shake_timer = 0.0
        self.boss_arena_locked = False
        self.boss_arena_left = 0
        self.boss_arena_right = 0

    def lock_boss_arena(self, arena_left, arena_right):
        self.boss_arena_locked = True
        self.boss_arena_left = arena_left
        self.boss_arena_right = arena_right

    def update(self, target_rect, target_vx, dt):
        target_x = target_rect.centerx - self.width // 2 + target_vx * 0.3
        target_y = target_rect.centery - self.height // 2

        self.offset_x += (target_x - self.offset_x) * min(CAMERA_LERP_SPEED * dt, 1.0)
        self.offset_y += (target_y - self.offset_y) * min(CAMERA_LERP_SPEED * dt, 1.0)

        # Boss arena lock limits horizontal movement
        if self.boss_arena_locked:
            self.offset_x = max(self.boss_arena_left, min(self.offset_x,
                               self.boss_arena_right - self.width))
        else:
            self.offset_x = max(0.0, min(self.offset_x, self.level_width - self.width))

        self.offset_y = max(0.0, min(self.offset_y, self.level_height - self.height))

        # Screen shake
        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.offset_x += random.randint(-self.shake_intensity, self.shake_intensity)
            self.offset_y += random.randint(-self.shake_intensity, self.shake_intensity)

    def shake(self, intensity, duration):
        self.shake_intensity = intensity
        self.shake_duration = duration
        self.shake_timer = duration

    def apply(self, rect):
        """Return a new rect offset to screen coordinates."""
        return rect.move(-int(self.offset_x), -int(self.offset_y))
