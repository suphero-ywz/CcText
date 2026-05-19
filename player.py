import pygame
from settings import *
from weapon import WEAPONS


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.hp = PLAYER_MAX_HP
        self.state = "idle"
        self.jump_cut = False
        self.rem_x = 0.0
        self.rem_y = 0.0

        # Attack
        self.attack_cooldown_timer = 0.0
        self.attack_phase = None  # "startup" | "active" | "recovery" | None
        self.attack_phase_timer = 0.0
        self.attack_hitbox = None

        # Invincibility / hurt
        self.invincibility_timer = 0.0
        self.hitstop_timer = 0.0
        self.hit_enemies = set()  # enemies already hit in current attack
        self.active_weapon = 0  # index into WEAPONS
        self._pending_projectile = False  # bow just fired, main.py spawns arrow
        self.jumps_left = 2
        self._jump_was_pressed = False

    def get_attack_hitbox(self):
        if self.attack_phase == "active" and self.attack_hitbox:
            return self.attack_hitbox
        return None

    @property
    def _weapon(self):
        return WEAPONS[self.active_weapon]

    def cycle_weapon(self):
        self.active_weapon = (self.active_weapon + 1) % len(WEAPONS)
        if self.attack_phase:
            self.attack_phase = None
            self.attack_phase_timer = 0
            self.attack_hitbox = None
            self.hit_enemies.clear()

    def get_pending_projectile(self):
        """Called by main.py each frame. Returns True once per bow shot."""
        if self._pending_projectile:
            self._pending_projectile = False
            return True
        return False

    def take_damage(self, amount, knockback_dir):
        if self.invincibility_timer > 0 or self.state == "dead":
            return False
        self.hp -= amount
        self.invincibility_timer = PLAYER_INVINCIBILITY_TIME
        self.state = "hit"
        self.vx = knockback_dir * PLAYER_KNOCKBACK_X
        self.vy = PLAYER_KNOCKBACK_Y
        if self.attack_phase:
            self.attack_phase = None
            self.attack_phase_timer = 0
            self.attack_hitbox = None
        if self.hp <= 0:
            self.hp = 0
            self.state = "dead"
        return True

    def update(self, dt, level, keys_down):
        def pressed(*keys):
            for k in keys:
                if k in keys_down:
                    return True
            return False

        # Always advance timers (even during hitstop)
        if self.hitstop_timer > 0:
            self.hitstop_timer -= dt
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= dt
        if self.invincibility_timer > 0:
            self.invincibility_timer -= dt

        # Advance attack phase machine (always, to prevent multi-hit extension)
        if self.attack_phase:
            w = self._weapon
            self.attack_phase_timer -= dt
            if self.attack_phase == "startup" and self.attack_phase_timer <= 0:
                self.attack_phase = "active"
                self.attack_phase_timer = w["active"]
                if w.get("type") == "ranged":
                    self._pending_projectile = True
                else:
                    self._build_attack_hitbox()
            elif self.attack_phase == "active":
                if w.get("type") == "ranged":
                    pass  # arrow already spawned, nothing to sustain
                else:
                    self._build_attack_hitbox()
                if self.attack_phase_timer <= 0:
                    self.attack_phase = "recovery"
                    self.attack_phase_timer = w["recovery"]
                    self.attack_hitbox = None
                    self.hit_enemies.clear()
            elif self.attack_phase == "recovery" and self.attack_phase_timer <= 0:
                self.attack_phase = None
                self.attack_hitbox = None
                self.hit_enemies.clear()

        # Hitstop — freeze physics, render continues
        if self.hitstop_timer > 0:
            return

        # Horizontal input (only when not attacking, or during startup)
        move_input = 0
        can_move = self.state not in ("hit", "dead")
        if can_move and (self.attack_phase is None or self.attack_phase == "startup"):
            if pressed(pygame.K_LEFT, pygame.KSCAN_LEFT, pygame.K_a, pygame.KSCAN_A):
                move_input = -1
            if pressed(pygame.K_RIGHT, pygame.KSCAN_RIGHT, pygame.K_d, pygame.KSCAN_D):
                move_input = 1

        # Acceleration / friction
        if move_input != 0:
            self.vx += move_input * PLAYER_SPEED_ACCEL * dt
            self.vx = max(-PLAYER_MAX_SPEED, min(PLAYER_MAX_SPEED, self.vx))
            self.facing = move_input
        else:
            if self.vx > 0:
                self.vx = max(0.0, self.vx - PLAYER_FRICTION * dt)
            elif self.vx < 0:
                self.vx = min(0.0, self.vx + PLAYER_FRICTION * dt)

        # Jump
        jump_pressed = pressed(pygame.K_UP, pygame.KSCAN_UP,
                               pygame.K_w, pygame.KSCAN_W,
                               pygame.K_SPACE, pygame.KSCAN_SPACE)
        # Reset jumps on ground
        if self.on_ground:
            self.jumps_left = 2
            self.jump_cut = False

        # First jump: can trigger on hold when on ground
        # Double jump: requires rising edge (release then press again)
        jump_just_pressed = jump_pressed and not self._jump_was_pressed
        can_jump = self.jumps_left > 0 and self.state not in ("hit", "dead")
        if can_jump and (jump_just_pressed or (jump_pressed and self.on_ground)):
            self.vy = PLAYER_JUMP_VEL
            self.on_ground = False
            self.jump_cut = False
            self.jumps_left -= 1

        # Variable jump height
        if not jump_pressed and self.vy < 0 and not self.jump_cut:
            self.vy *= PLAYER_JUMP_CUT
            self.jump_cut = True

        self._jump_was_pressed = jump_pressed

        # Gravity
        self.vy += PLAYER_GRAVITY * dt
        self.vy = min(self.vy, PLAYER_MAX_FALL)

        # Sub-pixel movement
        dx = self.vx * dt
        dy = self.vy * dt
        self.rem_x += dx
        self.rem_y += dy
        move_x = int(self.rem_x)
        move_y = int(self.rem_y)
        self.rem_x -= move_x
        self.rem_y -= move_y

        # Axis-separated collision
        self.rect.x += move_x
        level.resolve_collision_x(self, dx)

        self.rect.y += move_y
        level.resolve_collision_y(self, dy)

        # Attack input
        attack_pressed = pressed(pygame.K_j, pygame.KSCAN_J,
                                 pygame.K_z, pygame.KSCAN_Z)
        if attack_pressed and self.attack_phase is None and self.attack_cooldown_timer <= 0 \
                and self.state not in ("hit", "dead"):
            w = self._weapon
            self.attack_phase = "startup"
            self.attack_phase_timer = w["startup"]
            self.attack_cooldown_timer = w["cooldown"]
            self.attack_hitbox = None
            self.hit_enemies.clear()

        # Update state
        if self.state == "hit" and self.on_ground and abs(self.vx) < 20:
            self.state = "idle"

        if self.state not in ("hit", "dead"):
            if self.attack_phase:
                self.state = "attack"
            elif not self.on_ground:
                if self.vy < 0:
                    self.state = "jump"
                else:
                    self.state = "fall"
            elif abs(self.vx) > 10:
                self.state = "run"
            else:
                self.state = "idle"

    def _build_attack_hitbox(self):
        w = self._weapon
        hw = w["hitbox_width"]
        hh = w["hitbox_height"]
        offset = w["hitbox_offset_x"]
        hitbox_x = self.rect.centerx + self.facing * offset - (hw // 2 if self.facing > 0 else hw // 2)
        hitbox_y = self.rect.centery - hh // 2
        self.attack_hitbox = pygame.Rect(hitbox_x, hitbox_y, hw, hh)

    def render(self, screen, camera):
        screen_rect = camera.apply(self.rect)

        # Blink during invincibility (skip every other 0.1s)
        if self.invincibility_timer > 0 and int(self.invincibility_timer * 20) % 2 == 0:
            return

        color = BLUE
        if self.state == "hit":
            color = RED
        elif self.state == "dead":
            color = (60, 20, 20)
        pygame.draw.rect(screen, color, screen_rect)

        # Slash animation
        if self.attack_phase:
            self._render_slash(screen, screen_rect, camera)

        # Eye indicator
        eye_x = screen_rect.centerx + self.facing * 6
        eye_y = screen_rect.top + 12
        pygame.draw.circle(screen, WHITE, (eye_x, eye_y), 3)

    def _render_slash(self, screen, screen_rect, camera):
        import math
        w = self._weapon
        anim = w["anim_type"]
        if anim == "arc":
            self._render_arc_slash(screen, screen_rect)
        elif anim == "thrust":
            self._render_thrust(screen, screen_rect)
        elif anim == "overhead":
            self._render_overhead(screen, screen_rect)
        elif anim == "shoot":
            self._render_shoot(screen, screen_rect)

    def _render_arc_slash(self, screen, screen_rect):
        import math
        cx = screen_rect.centerx
        cy = screen_rect.centery
        f = self.facing
        w = self._weapon

        if self.attack_phase == "startup":
            t = 1.0 - self.attack_phase_timer / w["startup"]
            angle = math.radians(-100 * t)
            alpha = 0.6 + 0.4 * t
            length = 20 + 15 * t
        elif self.attack_phase == "active":
            t = 1.0 - self.attack_phase_timer / w["active"]
            angle = math.radians(-100 + 170 * t)
            alpha = 1.0
            length = 35
        elif self.attack_phase == "recovery":
            t = 1.0 - self.attack_phase_timer / w["recovery"]
            angle = math.radians(70)
            alpha = max(0.0, 1.0 - t)
            length = 30 + 10 * (1 - t)
        else:
            return

        trail_count = 4
        for i in range(trail_count):
            offset = (i - trail_count / 2) * 6
            trail_angle = angle + math.radians(offset * 0.25)
            trail_alpha = alpha * (0.25 + 0.15 * i)
            end_x = cx + math.cos(trail_angle) * (length - i * 3) * f
            end_y = cy + math.sin(trail_angle) * (length - i * 3)
            trail_color = (min(255, int(255 * trail_alpha)),
                           min(255, int(220 * trail_alpha)),
                           min(255, int(40 * trail_alpha)))
            pygame.draw.line(screen, trail_color,
                             (cx, cy), (int(end_x), int(end_y)), 3 - i // 2)

        end_x = cx + math.cos(angle) * length * f
        end_y = cy + math.sin(angle) * length
        main_alpha = min(255, int(255 * alpha))
        slash_color = (main_alpha, min(255, int(240 * alpha)), min(255, int(60 * alpha)))
        pygame.draw.line(screen, slash_color,
                         (cx, cy), (int(end_x), int(end_y)), 4)

        if self.attack_phase == "active":
            glow_radius = int(6 + 4 * abs(0.5 - (1.0 - self.attack_phase_timer / w["active"])))
            pygame.draw.circle(screen, YELLOW, (int(end_x), int(end_y)), glow_radius)

    def _render_thrust(self, screen, screen_rect):
        import math
        cx = screen_rect.centerx
        cy = screen_rect.centery
        f = self.facing
        w = self._weapon
        spear_color = w["color"]

        if self.attack_phase == "startup":
            t = 1.0 - self.attack_phase_timer / w["startup"]
            length = 8 + 28 * t
            alpha = 0.5 + 0.5 * t
        elif self.attack_phase == "active":
            t = 1.0 - self.attack_phase_timer / w["active"]
            length = 36 + 12 * (1 - t)
            alpha = 1.0
        elif self.attack_phase == "recovery":
            t = 1.0 - self.attack_phase_timer / w["recovery"]
            length = 48 - 20 * t
            alpha = max(0.0, 1.0 - t)
        else:
            return

        # Draw spear shaft (straight line)
        end_x = cx + length * f
        end_y = cy
        a = min(255, int(255 * alpha))
        shaft_color = (min(255, int(spear_color[0] * alpha)),
                       min(255, int(spear_color[1] * alpha)),
                       min(255, int(spear_color[2] * alpha)))
        pygame.draw.line(screen, shaft_color, (cx, cy), (int(end_x), int(end_y)), 3)

        # Tip glow
        if self.attack_phase == "active":
            glow_r = int(5 + 3 * abs(0.5 - t))
            pygame.draw.circle(screen, (200, 255, 255), (int(end_x), int(end_y)), glow_r)

    def _render_overhead(self, screen, screen_rect):
        import math
        cx = screen_rect.centerx
        cy = screen_rect.centery
        f = self.facing
        w = self._weapon
        axe_color = w["color"]

        if self.attack_phase == "startup":
            t = 1.0 - self.attack_phase_timer / w["startup"]
            angle = math.radians(-90 - 60 * t)
            alpha = 0.5 + 0.5 * t
            length = 28 + 10 * t
        elif self.attack_phase == "active":
            t = 1.0 - self.attack_phase_timer / w["active"]
            angle = math.radians(-150 + 120 * t)
            alpha = 1.0
            length = 38
        elif self.attack_phase == "recovery":
            t = 1.0 - self.attack_phase_timer / w["recovery"]
            angle = math.radians(-30 + 50 * (1 - t))
            alpha = max(0.0, 1.0 - t)
            length = 38
        else:
            return

        # Heavy trail
        trail_count = 3
        for i in range(trail_count):
            trail_off = (i - trail_count / 2) * 8
            trail_angle = angle + math.radians(trail_off * 0.3)
            trail_alpha = alpha * (0.2 + 0.2 * i)
            end_x = cx + math.cos(trail_angle) * (length - i * 4) * f
            end_y = cy - math.sin(trail_angle) * (length - i * 4)
            tc = (min(255, int(axe_color[0] * trail_alpha)),
                  min(255, int(axe_color[1] * trail_alpha)),
                  min(255, int(axe_color[2] * trail_alpha)))
            pygame.draw.line(screen, tc, (cx, cy - 5),
                             (int(end_x), int(end_y)), 5 - i)

        # Main arc
        end_x = cx + math.cos(angle) * length * f
        end_y = cy - math.sin(angle) * length
        a = min(255, int(255 * alpha))
        main_color = (min(255, int(axe_color[0] * alpha)),
                      min(255, int(axe_color[1] * alpha)),
                      min(255, int(axe_color[2] * alpha)))
        pygame.draw.line(screen, main_color, (cx, cy - 5),
                         (int(end_x), int(end_y)), 5)

        # Impact glow at tip during active
        if self.attack_phase == "active":
            glow_r = int(7 + 5 * abs(0.5 - t))
            pygame.draw.circle(screen, (255, 200, 60),
                               (int(end_x), int(end_y)), glow_r)

    def _render_shoot(self, screen, screen_rect):
        cx = screen_rect.centerx
        cy = screen_rect.centery
        f = self.facing
        w = self._weapon

        if self.attack_phase == "startup":
            t = 1.0 - self.attack_phase_timer / w["startup"]
            # Draw bowstring pulling back
            alpha = 0.4 + 0.6 * t
            pullback = 8 + 16 * t
            bow_color = (min(255, int(w["color"][0] * alpha)),
                         min(255, int(w["color"][1] * alpha)),
                         min(255, int(w["color"][2] * alpha)))
            # Bow arc (curve toward facing direction)
            bow_x = cx + f * pullback * 0.3
            pygame.draw.line(screen, bow_color,
                             (cx, cy - 10), (bow_x, cy), 2)
            pygame.draw.line(screen, bow_color,
                             (cx, cy + 10), (bow_x, cy), 2)
            # String tension line
            string_color = (min(255, int(200 * alpha)),
                            min(255, int(200 * alpha)),
                            min(255, int(200 * alpha)))
            pygame.draw.line(screen, string_color,
                             (cx - f * 6, cy - 8),
                             (cx - f * 6, cy + 8), 2)
        elif self.attack_phase == "active":
            # Flash at release point
            flash_r = 10
            flash_color = (200, 255, 200)
            pygame.draw.circle(screen, flash_color,
                               (cx + f * 10, cy), flash_r, 1)
            # Arrow trail hint
            trail_color = (140, 255, 140)
            pygame.draw.line(screen, trail_color,
                             (cx, cy), (cx + f * 22, cy), 1)
        elif self.attack_phase == "recovery":
            t = 1.0 - self.attack_phase_timer / w["recovery"]
            alpha = max(0.0, 1.0 - t)
            bow_color = (min(255, int(w["color"][0] * alpha)),
                         min(255, int(w["color"][1] * alpha)),
                         min(255, int(w["color"][2] * alpha)))
            pygame.draw.line(screen, bow_color,
                             (cx, cy - 6), (cx + f * 4, cy), 1)
            pygame.draw.line(screen, bow_color,
                             (cx, cy + 6), (cx + f * 4, cy), 1)

    def can_hit_enemy(self, enemy):
        """Check if enemy hasn't been hit yet in this attack swing."""
        return id(enemy) not in self.hit_enemies

    def mark_enemy_hit(self, enemy):
        """Record that enemy was hit in this attack swing."""
        self.hit_enemies.add(id(enemy))

    def set_hitstop(self, duration):
        self.hitstop_timer = duration
