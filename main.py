import pygame
import sys
import traceback
from settings import *
from level import Level, BOSS_ARENA_START_COL
from player import Player
from camera import Camera
from enemy import PatrolEnemy, FlyingEnemy, BossEnemy
from particles import ParticleSystem
from projectile import Arrow
from ui import UI


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Geometric Blade")
        pygame.key.stop_text_input()
        self.clock = pygame.time.Clock()
        self.state = "MENU"
        self.keys_down = set()
        self.ui = UI(self.screen)
        self.particles = ParticleSystem()
        self.enemies = []
        self.boss = None
        self.projectiles = []
        self.reset_game()

    def reset_game(self):
        self.level = Level()
        self.player = Player(100, 17 * TILE_SIZE - PLAYER_HEIGHT)
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT,
                             self.level.width, self.level.height)
        self.particles = ParticleSystem()
        self.enemies = self._spawn_enemies()
        self.boss = None
        self.boss_spawned = False
        self.projectiles = []

    def _spawn_enemies(self):
        enemies = [
            # Section 1: intro patrols
            PatrolEnemy(8 * TILE_SIZE, 17 * TILE_SIZE - 40),
            PatrolEnemy(14 * TILE_SIZE, 17 * TILE_SIZE - 40),
            # Section 2: platform enemies
            PatrolEnemy(30 * TILE_SIZE, 13 * TILE_SIZE - 40, patrol_range=160),
            PatrolEnemy(42 * TILE_SIZE, 17 * TILE_SIZE - 40),
            # Flying enemies
            FlyingEnemy(22 * TILE_SIZE, 10 * TILE_SIZE),
            FlyingEnemy(48 * TILE_SIZE, 8 * TILE_SIZE),
            FlyingEnemy(68 * TILE_SIZE, 9 * TILE_SIZE),
            # Section 3
            PatrolEnemy(58 * TILE_SIZE, 17 * TILE_SIZE - 40, patrol_range=200),
            PatrolEnemy(70 * TILE_SIZE, 12 * TILE_SIZE - 40, patrol_range=120),
            FlyingEnemy(85 * TILE_SIZE, 7 * TILE_SIZE),
            # Section 4: pre-boss
            PatrolEnemy(100 * TILE_SIZE, 17 * TILE_SIZE - 40),
            PatrolEnemy(108 * TILE_SIZE, 10 * TILE_SIZE - 40, patrol_range=150),
            FlyingEnemy(118 * TILE_SIZE, 8 * TILE_SIZE),
            PatrolEnemy(125 * TILE_SIZE, 17 * TILE_SIZE - 40),
        ]
        return enemies

    def _try_spawn_boss(self):
        if self.boss_spawned:
            return
        if self.player.rect.centerx >= self.level.boss_arena_start:
            bx, by = self.level.boss_spawn
            self.boss = BossEnemy(bx, by - 80)
            self.boss_spawned = True
            self.camera.lock_boss_arena(
                self.level.boss_arena_start,
                self.level.boss_arena_start + (160 - BOSS_ARENA_START_COL) * TILE_SIZE
            )

    def run(self):
        while True:
            try:
                dt = min(self.clock.tick(FPS) / 1000.0, MAX_DT)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        self.keys_down.add(event.key)
                        self.keys_down.add(event.scancode)
                        if event.key == pygame.K_ESCAPE or event.scancode == pygame.KSCAN_ESCAPE:
                            if self.state == "PLAYING":
                                self.state = "PAUSED"
                            elif self.state == "PAUSED":
                                self.state = "PLAYING"
                        if event.key == pygame.K_q or event.scancode == pygame.KSCAN_Q:
                            if self.state == "PLAYING":
                                self.player.cycle_weapon()
                        if event.key == pygame.K_RETURN or event.scancode == pygame.KSCAN_RETURN:
                            if self.state == "MENU":
                                self.state = "PLAYING"
                                self.reset_game()
                            elif self.state == "GAME_OVER":
                                self.state = "MENU"
                            elif self.state == "WIN":
                                self.state = "MENU"
                    elif event.type == pygame.KEYUP:
                        self.keys_down.discard(event.key)
                        self.keys_down.discard(event.scancode)

                if self.state == "PLAYING":
                    self._update(dt)

                self.render()
            except Exception as e:
                print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
                traceback.print_exc()
                pygame.quit()
                sys.exit(1)

    def _update(self, dt):
        self.player.update(dt, self.level, self.keys_down)

        # Boss arena lock
        self._try_spawn_boss()

        for enemy in self.enemies:
            enemy.update(dt, self.level, self.player)
        if self.boss:
            self.boss.update(dt, self.level, self.player)

        # Remove dead regular enemies
        for enemy in self.enemies[:]:
            if not enemy.alive:
                self.particles.enemy_death(enemy.rect.centerx, enemy.rect.centery,
                                           enemy.color)
                self.enemies.remove(enemy)

        # Player attack vs enemies
        attack_hitbox = self.player.get_attack_hitbox()
        if attack_hitbox:
            w = self.player._weapon
            dmg = w["damage"]
            pierce = w["pierce"]
            # Check boss first
            if self.boss and self.boss.alive and self.player.can_hit_enemy(self.boss):
                if attack_hitbox.colliderect(self.boss.rect):
                    kb_dir = self.player.facing
                    self.boss.take_damage(dmg, kb_dir)
                    self.player.mark_enemy_hit(self.boss)
                    self.particles.attack_hit(
                        self.boss.rect.centerx + kb_dir * -10,
                        self.boss.rect.centery,
                        self.player.facing
                    )
                    self.particles.add_damage_number(
                        self.boss.rect.centerx, self.boss.rect.top, dmg
                    )
                    self.player.set_hitstop(HITSTOP_KILL if not self.boss.alive else HITSTOP_ATTACK)
                    if not self.boss.alive:
                        self.camera.shake(SHAKE_BOSS_DEATH, 0.5)
                    else:
                        shake_intensity = SHAKE_BOSS_ATTACK
                        if w["anim_type"] == "overhead":
                            shake_intensity = SHAKE_BOSS_ATTACK + 6
                        self.camera.shake(shake_intensity, 0.15)
            # Then regular enemies
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                if not self.player.can_hit_enemy(enemy):
                    continue
                if attack_hitbox.colliderect(enemy.rect):
                    kb_dir = self.player.facing
                    enemy.take_damage(dmg, kb_dir)
                    self.player.mark_enemy_hit(enemy)
                    self.particles.attack_hit(
                        enemy.rect.centerx + kb_dir * -10,
                        enemy.rect.centery,
                        self.player.facing
                    )
                    self.particles.add_damage_number(
                        enemy.rect.centerx, enemy.rect.top, dmg
                    )
                    self.player.set_hitstop(HITSTOP_ATTACK)
                    if not pierce:
                        break

        # Spawn arrow from bow
        if self.player.get_pending_projectile():
            w = self.player._weapon
            arrow = Arrow(self.player.rect.centerx, self.player.rect.centery,
                          self.player.facing, w["damage"])
            self.projectiles.append(arrow)

        # Update arrows + collision
        for arrow in self.projectiles[:]:
            arrow.update(dt, self.level)
            if not arrow.alive:
                self.projectiles.remove(arrow)
                continue
            hit = False
            # Check boss
            if self.boss and self.boss.alive and arrow.rect.colliderect(self.boss.rect):
                kb_dir = 1 if arrow.vx > 0 else -1
                self.boss.take_damage(arrow.damage, kb_dir)
                self.particles.attack_hit(arrow.x, arrow.y, arrow.facing)
                self.particles.add_damage_number(arrow.x, arrow.y - 10, arrow.damage)
                self.camera.shake(SHAKE_BOSS_ATTACK if self.boss.alive else SHAKE_BOSS_DEATH, 0.15)
                arrow.alive = False
                hit = True
            if not hit:
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if arrow.rect.colliderect(enemy.rect):
                        kb_dir = 1 if arrow.vx > 0 else -1
                        enemy.take_damage(arrow.damage, kb_dir)
                        self.particles.attack_hit(arrow.x, arrow.y, arrow.facing)
                        self.particles.add_damage_number(arrow.x, arrow.y - 10, arrow.damage)
                        arrow.alive = False
                        break

        # Camera shake on player hurt
        if self.player.state == "hit":
            self.camera.shake(SHAKE_PLAYER_HURT, 0.12)

        self.particles.update(dt)
        self.camera.update(self.player.rect, self.player.vx, dt)

        # Death
        if self.player.state == "dead":
            self.state = "GAME_OVER"

        # Victory: boss dead
        if self.boss_spawned and self.boss and not self.boss.alive:
            self.state = "WIN"

    def render(self):
        self.screen.fill(BG_COLOR)

        if self.state == "MENU":
            self.ui.draw_menu()
        elif self.state in ("PLAYING", "PAUSED", "GAME_OVER", "WIN"):
            self.level.render(self.screen, self.camera)

            # Collect all entities for Y-sorted rendering
            entities = list(self.enemies)
            if self.boss and self.boss.alive:
                entities.append(self.boss)
            entities.sort(key=lambda e: e.rect.bottom)

            for entity in entities:
                entity.render(self.screen, self.camera)

            for arrow in self.projectiles:
                arrow.render(self.screen, self.camera)

            self.particles.render(self.screen, self.camera)
            self.player.render(self.screen, self.camera)

            # Player HP bar
            self._draw_player_hp_bar()

            # Boss HP bar
            if self.boss and self.boss.alive:
                self.ui.draw_boss_hp_bar(self.boss.hp, self.boss.max_hp)

            # Overlays
            if self.state == "PAUSED":
                self.ui.draw_pause()
            elif self.state == "GAME_OVER":
                self.ui.draw_game_over()
            elif self.state == "WIN":
                self.ui.draw_victory()

        pygame.display.flip()

    def _draw_player_hp_bar(self):
        w = self.player._weapon
        bar_w = HP_BAR_WIDTH
        bar_h = HP_BAR_HEIGHT
        bar_y = SCREEN_HEIGHT - HP_BAR_Y - bar_h

        # --- HP label ---
        hp_label = self.ui.font_small.render("HP", True, WHITE)
        lw = hp_label.get_width()

        # --- HP fraction text ---
        pct = int(self.player.hp / PLAYER_MAX_HP * 100)
        hp_text = self.ui.font_small.render(
            f"{pct}%", True, (180, 180, 200))
        tw = hp_text.get_width()

        # --- Weapon indicator ---
        wp_color = w["color"]
        wp_name = w["name"]
        icon_s = 8
        wp_label = self.ui.font_small.render(wp_name, True, wp_color)
        wp_w = icon_s + 6 + wp_label.get_width()

        # --- Layout: center all elements in one row ---
        gap1 = 10  # HP label <-> bar
        gap2 = 10  # bar <-> fraction
        gap3 = 24  # fraction <-> weapon
        total_w = lw + gap1 + bar_w + gap2 + tw + gap3 + wp_w
        start_x = (SCREEN_WIDTH - total_w) // 2

        # HP label
        self.screen.blit(hp_label, (start_x, bar_y))

        # HP bar track
        bar_x = start_x + lw + gap1
        pygame.draw.rect(self.screen, (20, 20, 25),
                         (bar_x, bar_y, bar_w, bar_h))
        # HP fill
        if self.player.hp > 0:
            ratio = self.player.hp / PLAYER_MAX_HP
            fill_w = int(bar_w * ratio)
            if ratio > 0.5:
                fc = GREEN
            elif ratio > 0.25:
                fc = YELLOW
            else:
                fc = RED
            pygame.draw.rect(self.screen, fc, (bar_x, bar_y, fill_w, bar_h))
            # Shine on fill
            s = min(255, int(80 * ratio))
            pygame.draw.line(self.screen, (s, s, s),
                             (bar_x + 2, bar_y + 2),
                             (bar_x + fill_w - 2, bar_y + 2), 1)
        # Bar border
        pygame.draw.rect(self.screen, WHITE,
                         (bar_x, bar_y, bar_w, bar_h), 1)
        # Segments
        sw = bar_w // PLAYER_MAX_HP
        for i in range(1, PLAYER_MAX_HP):
            sx = bar_x + i * sw
            pygame.draw.line(self.screen, (30, 30, 35),
                             (sx, bar_y + 1), (sx, bar_y + bar_h - 1), 1)

        # HP fraction
        self.screen.blit(hp_text, (bar_x + bar_w + gap2, bar_y - 1))

        # Weapon icon + name
        wx = bar_x + bar_w + gap2 + tw + gap3
        wy = bar_y
        pygame.draw.rect(self.screen, wp_color,
                         (wx, wy + 4, icon_s, icon_s))
        pygame.draw.rect(self.screen, WHITE,
                         (wx, wy + 4, icon_s, icon_s), 1)
        self.screen.blit(wp_label, (wx + icon_s + 6, wy - 1))


if __name__ == "__main__":
    Game().run()
