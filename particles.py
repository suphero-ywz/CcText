import random
import pygame
from settings import *


class Particle:
    def __init__(self, x, y, vx, vy, lifetime, color, size=3):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size
        self.alive = True

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        self.vy += PARTICLE_GRAVITY * dt
        damping = max(0.0, 1.0 - PARTICLE_FRICTION * dt)
        self.vx *= damping
        self.x += self.vx * dt
        self.y += self.vy * dt

    def render(self, screen, camera):
        if not self.alive:
            return
        alpha = max(0.0, min(1.0, self.lifetime / self.max_lifetime))
        color = tuple(min(255, int(c * alpha)) for c in self.color)
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y)
        pygame.draw.rect(screen, color, (sx, sy, self.size, self.size))


class DamageNumber:
    def __init__(self, x, y, amount):
        self.x = x
        self.y = y
        self.amount = amount
        self.lifetime = DAMAGE_NUMBER_DURATION
        self.max_lifetime = DAMAGE_NUMBER_DURATION
        self.alive = True

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.alive = False
            return
        self.y += DAMAGE_NUMBER_SPEED * dt

    def render(self, screen, camera, font):
        if not self.alive:
            return
        alpha = max(0, min(1, self.lifetime / self.max_lifetime))
        sx = int(self.x - camera.offset_x)
        sy = int(self.y - camera.offset_y - self.max_lifetime * 0.3 * DAMAGE_NUMBER_SPEED)
        text = font.render(str(self.amount), True, WHITE)
        text.set_alpha(int(255 * alpha))
        text_rect = text.get_rect(center=(sx, sy))
        screen.blit(text, text_rect)


class ParticleSystem:
    def __init__(self):
        self.particles = []
        self.damage_numbers = []
        self._font = None

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.Font(None, 24)
        return self._font

    def emit(self, x, y, count, color, speed_range, lifetime_range, size=3):
        for _ in range(count):
            angle = random.uniform(0, 6.2832)
            speed = random.uniform(*speed_range)
            vx = speed * 1.4 * random.uniform(-1, 1) if speed_range[1] > 0 else speed * 0.3
            vy = random.uniform(*speed_range) if speed_range[1] < 0 else -speed * random.uniform(0.3, 1.0)
            lifetime = random.uniform(*lifetime_range)
            self.particles.append(Particle(x, y, vx, vy, lifetime, color, size))

    def attack_hit(self, x, y, facing):
        count = random.randint(5, 8)
        for _ in range(count):
            vx = facing * random.uniform(80, 200)
            vy = random.uniform(-180, -40)
            lifetime = random.uniform(0.15, 0.35)
            color = random.choice([WHITE, YELLOW])
            self.particles.append(Particle(x, y, vx, vy, lifetime, color, 3))

    def enemy_death(self, x, y, color):
        count = random.randint(15, 20)
        for _ in range(count):
            angle = random.uniform(0, 6.2832)
            speed = random.uniform(60, 220)
            vx = speed * 1.2 * random.uniform(-1, 1)
            vy = -speed * random.uniform(0.4, 1.0)
            lifetime = random.uniform(0.2, 0.5)
            self.particles.append(Particle(x, y, vx, vy, lifetime, color, 3))

    def add_damage_number(self, x, y, amount):
        self.damage_numbers.append(DamageNumber(x, y, amount))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        for dn in self.damage_numbers:
            dn.update(dt)
        self.damage_numbers = [dn for dn in self.damage_numbers if dn.alive]

    def render(self, screen, camera):
        for p in self.particles:
            p.render(screen, camera)
        for dn in self.damage_numbers:
            dn.render(screen, camera, self.font)
