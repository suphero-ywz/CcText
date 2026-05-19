import pygame
from settings import *


class BaseEnemy:
    def __init__(self, x, y, width, height, hp, damage, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.vx = 0.0
        self.vy = 0.0
        self.hp = hp
        self.max_hp = hp
        self.damage = damage
        self.color = color
        self.alive = True
        self.on_ground = False
        self.rem_x = 0.0
        self.rem_y = 0.0
        self.flash_timer = 0.0
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

    def take_damage(self, amount, knockback_dir, particle_sys=None):
        if not self.alive:
            return False
        self.hp -= amount
        self.flash_timer = ENEMY_WHITEFLASH_TIME
        self.knockback_vx = knockback_dir * ENEMY_KNOCKBACK_X
        self.knockback_vy = ENEMY_KNOCKBACK_Y
        self.on_ground = False
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return True

    def update_physics(self, dt, level):
        if self.flash_timer > 0:
            self.flash_timer -= dt

        # Apply knockback
        if self.knockback_vx != 0 or self.knockback_vy != 0:
            self.vy = self.knockback_vy
            self.vx = self.knockback_vx
            self.knockback_vx = 0
            self.knockback_vy = 0

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

        self.rect.x += move_x
        level.resolve_collision_x(self, dx)

        self.rect.y += move_y
        level.resolve_collision_y(self, dy)

    def check_player_contact(self, player):
        if not self.alive:
            return False
        if player.invincibility_timer > 0 or player.state == "dead":
            return False
        if self.rect.colliderect(player.rect):
            knockback_dir = 1 if player.rect.centerx >= self.rect.centerx else -1
            player.take_damage(self.damage, knockback_dir)
            return True
        return False

    def render(self, screen, camera):
        if not self.alive:
            return
        screen_rect = camera.apply(self.rect)
        color = WHITE if self.flash_timer > 0 else self.color
        pygame.draw.rect(screen, color, screen_rect)
        # Eyes
        eye_x = screen_rect.centerx + 4
        eye_y = screen_rect.top + 8
        pygame.draw.circle(screen, BLACK, (eye_x, eye_y), 2)
        # HP bar
        if self.hp < self.max_hp:
            self._render_hp_bar(screen, screen_rect)

    def _render_hp_bar(self, screen, screen_rect):
        bar_w = ENEMY_HP_BAR_WIDTH
        bar_h = ENEMY_HP_BAR_HEIGHT
        bar_x = screen_rect.centerx - bar_w // 2
        bar_y = screen_rect.top - ENEMY_HP_BAR_OFFSET_Y - bar_h
        # Background
        pygame.draw.rect(screen, (40, 10, 10), (bar_x, bar_y, bar_w, bar_h))
        # Fill
        fill_w = int(bar_w * self.hp / self.max_hp)
        if fill_w > 0:
            fill_color = GREEN if self.hp > self.max_hp // 2 else YELLOW if self.hp > 1 else RED
            pygame.draw.rect(screen, fill_color, (bar_x, bar_y, fill_w, bar_h))


class PatrolEnemy(BaseEnemy):
    def __init__(self, x, y, patrol_range=None):
        super().__init__(x, y, 28, 40, hp=3, damage=1, color=ENEMY_PATROL_COLOR)
        self.patrol_speed = PATROL_SPEED
        self.patrol_dir = 1
        self.vx = PATROL_SPEED
        self.patrol_range = patrol_range
        self.spawn_x = x
        self.aggro = False
        self._jumping = False  # true when AI voluntarily jumped (ledge/gap)

    def update(self, dt, level, player):
        if not self.alive:
            return

        # Remember knockback state before physics consumes it
        had_knockback = self.knockback_vx != 0 or self.knockback_vy != 0

        self.update_physics(dt, level)

        # update_physics may have zeroed vx via collision resolution.
        # Restore horizontal speed if in a voluntary jump (ledge step / gap).
        # Don't fight knockback — if the enemy just got hit, let it fly.
        if self._jumping and not self.on_ground and not had_knockback:
            speed = PATROL_CHASE_SPEED if self.aggro else self.patrol_speed
            self.vx = self.patrol_dir * speed

        # Restore patrol speed on ground
        if self.on_ground:
            self.vx = self.patrol_dir * self.patrol_speed
            self._jumping = False

        # Aggro check
        dist_x = abs(self.rect.centerx - player.rect.centerx)
        dist_y = abs(self.rect.centery - player.rect.centery)
        self.aggro = dist_x < PATROL_AGGRO_RANGE and dist_y < 100

        speed = PATROL_CHASE_SPEED if self.aggro else self.patrol_speed

        if self.aggro:
            self.patrol_dir = 1 if player.rect.centerx > self.rect.centerx else -1
            if self.on_ground:
                self.vx = self.patrol_dir * speed
            direction = self.patrol_dir
        else:
            direction = self.patrol_dir
            if self.on_ground:
                self.vx = self.patrol_dir * speed

        if self.on_ground:
            ahead_col = (self.rect.right + 2) // TILE_SIZE if direction > 0 else (self.rect.left - 2) // TILE_SIZE
            if not (0 <= ahead_col < level.cols):
                self.patrol_dir = -self.patrol_dir
                self.vx = self.patrol_dir * speed
            else:
                foot_row = (self.rect.bottom - 1) // TILE_SIZE
                mid_row = self.rect.centery // TILE_SIZE
                head_row = self.rect.top // TILE_SIZE
                above_head_row = head_row - 1

                def solid(row):
                    return 0 <= row < level.rows and level.is_solid(ahead_col, row)

                solid_foot = solid(foot_row)
                solid_mid = solid(mid_row)
                solid_head = solid(head_row)
                solid_above_head = solid(above_head_row)

                ground_col = (self.rect.centerx + direction * 16) // TILE_SIZE
                ground_row = (self.rect.bottom + 2) // TILE_SIZE
                has_ground = (
                    0 <= ground_col < level.cols and
                    0 <= ground_row < level.rows and
                    level.is_solid(ground_col, ground_row)
                )
                has_ground_below = (
                    0 <= ground_col < level.cols and
                    0 <= ground_row + 1 < level.rows and
                    level.is_solid(ground_col, ground_row + 1)
                )

                if solid_above_head:
                    self.patrol_dir = -self.patrol_dir
                    self.vx = self.patrol_dir * speed
                elif solid_head or solid_mid or solid_foot:
                    self.vy = PLAYER_JUMP_VEL
                    self.on_ground = False
                    self.vx = self.patrol_dir * speed
                    self._jumping = True
                elif not has_ground and has_ground_below:
                    self.vy = PLAYER_JUMP_VEL
                    self.on_ground = False
                    self.vx = self.patrol_dir * speed
                    self._jumping = True
                elif not has_ground and not has_ground_below:
                    self.patrol_dir = -self.patrol_dir
                    self.vx = self.patrol_dir * speed

            if not self.aggro and self.patrol_range is not None:
                if self.rect.centerx < self.spawn_x - self.patrol_range // 2:
                    self.patrol_dir = 1
                    self.vx = self.patrol_speed
                elif self.rect.centerx > self.spawn_x + self.patrol_range // 2:
                    self.patrol_dir = -1
                    self.vx = -self.patrol_speed

        self.check_player_contact(player)

    def render(self, screen, camera):
        if not self.alive:
            return
        screen_rect = camera.apply(self.rect)
        color = WHITE if self.flash_timer > 0 else self.color
        if self.aggro and self.flash_timer <= 0:
            color = (255, 100, 30)  # bright red-orange when aggro
        pygame.draw.rect(screen, color, screen_rect)
        eye_x = screen_rect.centerx + 4
        eye_y = screen_rect.top + 8
        eye_color = YELLOW if self.aggro else BLACK
        pygame.draw.circle(screen, eye_color, (eye_x, eye_y), 2)
        if self.hp < self.max_hp:
            self._render_hp_bar(screen, screen_rect)


class FlyingEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y, 30, 30, hp=2, damage=1, color=ENEMY_FLYING_COLOR)
        self.base_x = x
        self.base_y = y
        self.hover_time = 0.0
        self.aggro = False

    def update(self, dt, level, player):
        if not self.alive:
            return
        if self.flash_timer > 0:
            self.flash_timer -= dt

        # Apply knockback
        if self.knockback_vx != 0 or self.knockback_vy != 0:
            self.vx = self.knockback_vx
            self.vy = self.knockback_vy
            self.knockback_vx = 0
            self.knockback_vy = 0

        self.hover_time += dt

        dist = abs(self.rect.centerx - player.rect.centerx)
        dist_y = abs(self.rect.centery - player.rect.centery)
        self.aggro = dist < FLYING_AGGRO_RANGE and dist_y < 200

        if self.aggro:
            # Chase player horizontally
            direction = 1 if player.rect.centerx > self.rect.centerx else -1
            self.vx = direction * FLYING_CHASE_SPEED
            # Chase vertically (mild)
            if abs(player.rect.centery - self.rect.centery) > 20:
                dir_y = 1 if player.rect.centery > self.rect.centery else -1
                self.vy = dir_y * FLYING_CHASE_SPEED * 0.6
            else:
                self.vy *= 0.9
        else:
            # Return to base position
            if abs(self.rect.centerx - self.base_x) > 5:
                direction = 1 if self.base_x > self.rect.centerx else -1
                self.vx = direction * PATROL_SPEED * 0.5
            else:
                self.vx *= 0.9
                self.rect.centerx = self.base_x
            # Hover
            self.vy = (self.base_y + FLYING_HOVER_AMP * 0.5 -
                       self.rect.centery) * 2.0

        # Hover bob
        hover_offset = FLYING_HOVER_AMP * 0.5 * (1 + self.hover_time % 1.0 * 0.1)

        # Apply velocity
        self.rect.x += self.vx * dt
        self.rect.y += self.vy * dt

        # Clamp to level bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > level.width:
            self.rect.right = level.width
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > level.height:
            self.rect.bottom = level.height

        self.check_player_contact(player)

    def render(self, screen, camera):
        if not self.alive:
            return
        screen_rect = camera.apply(self.rect)
        color = WHITE if self.flash_timer > 0 else self.color
        pygame.draw.rect(screen, color, screen_rect)
        # Wings
        wing_offset = int(3 * (1 + self.hover_time * 8 % 2))
        pygame.draw.rect(screen, color,
                         (screen_rect.left - 6, screen_rect.top + wing_offset, 6, 16))
        pygame.draw.rect(screen, color,
                         (screen_rect.right, screen_rect.top + wing_offset, 6, 16))
        # Eyes
        eye_x = screen_rect.centerx + 4
        eye_y = screen_rect.top + 8
        pygame.draw.circle(screen, BLACK, (eye_x, eye_y), 2)
        if self.hp < self.max_hp:
            self._render_hp_bar(screen, screen_rect)


class BossEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y, 80, 80, hp=BOSS_HP, damage=BOSS_DAMAGE,
                         color=BOSS_COLOR_P1)
        self.boss_state = "patrol"  # patrol | windup | charge | stun | ground_slam
        self.boss_timer = 0.0
        self.charge_direction = 1
        self.phase = 1
        self.windup_flash = 0.0
        self.ground_slam_cooldown = 0.0

    def update(self, dt, level, player):
        if not self.alive:
            return

        # Phase transition
        if self.hp <= BOSS_HP * BOSS_P2_HP_RATIO and self.phase == 1:
            self.phase = 2
            self.color = BOSS_COLOR_P2

        # Timers
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.ground_slam_cooldown > 0:
            self.ground_slam_cooldown -= dt
        self.boss_timer -= dt

        # Apply knockback (reduced)
        if self.knockback_vx != 0 or self.knockback_vy != 0:
            self.vy = self.knockback_vy * BOSS_KNOCKBACK_RESIST
            self.vx = self.knockback_vx * BOSS_KNOCKBACK_RESIST
            self.knockback_vx = 0
            self.knockback_vy = 0
            self.on_ground = False

        # Physics
        self.vy += PLAYER_GRAVITY * dt
        self.vy = min(self.vy, PLAYER_MAX_FALL)

        dx = self.vx * dt
        dy = self.vy * dt
        self.rem_x += dx
        self.rem_y += dy
        move_x = int(self.rem_x)
        move_y = int(self.rem_y)
        self.rem_x -= move_x
        self.rem_y -= move_y

        self.rect.x += move_x
        level.resolve_collision_x(self, dx)

        self.rect.y += move_y
        level.resolve_collision_y(self, dy)

        if self.on_ground and self.vy >= 0:
            self.vy = 0

        # Boss AI state machine
        patrol_speed = BOSS_P2_PATROL_SPEED if self.phase == 2 else BOSS_PATROL_SPEED
        charge_speed = BOSS_P2_CHARGE_SPEED if self.phase == 2 else BOSS_CHARGE_SPEED

        if self.boss_state == "patrol":
            # Face toward player
            self.vx = patrol_speed if player.rect.centerx > self.rect.centerx else -patrol_speed
            # Check if should transition to windup
            dist = abs(self.rect.centerx - player.rect.centerx)
            if dist < 300 and self.on_ground:
                self.boss_state = "windup"
                self.boss_timer = BOSS_CHARGE_WINDUP
                self.vx = 0
                self.windup_flash = 0.0

        elif self.boss_state == "windup":
            self.windup_flash += dt
            if self.boss_timer <= 0:
                self.boss_state = "charge"
                self.charge_direction = 1 if player.rect.centerx > self.rect.centerx else -1
                # If in P2 and cooldown ready, sometimes ground slam instead
                if self.phase == 2 and self.ground_slam_cooldown <= 0 and abs(
                        player.rect.centerx - self.rect.centerx) < BOSS_GROUND_SLAM_RANGE:
                    self.boss_state = "ground_slam"
                    self.vy = BOSS_GROUND_SLAM_JUMP
                    self.on_ground = False
                    self.ground_slam_cooldown = 3.0
                else:
                    self.vx = self.charge_direction * charge_speed

        elif self.boss_state == "charge":
            # Keep charging until hitting wall
            if not self.on_ground and self.vy < 0:
                pass  # Still charging in air
            # Check wall collision (vx was zeroed by collision)
            if self.on_ground and abs(self.vx) < 10:
                self.boss_state = "stun"
                self.boss_timer = BOSS_STUN_TIME
                self.vx = 0
            # Also stun after charge time limit
            if self.boss_timer <= -2.0:
                self.boss_state = "stun"
                self.boss_timer = BOSS_STUN_TIME
                self.vx = 0

        elif self.boss_state == "ground_slam":
            if self.on_ground:
                self.boss_state = "stun"
                self.boss_timer = BOSS_STUN_TIME * 0.5
                self.vx = 0

        elif self.boss_state == "stun":
            self.vx = 0
            if self.boss_timer <= 0:
                self.boss_state = "patrol"

        # Track charge time
        if self.boss_state == "charge":
            self.boss_timer -= dt

        self.check_player_contact(player)

    def take_damage(self, amount, knockback_dir, particle_sys=None):
        if not self.alive:
            return False
        self.hp -= amount
        self.flash_timer = ENEMY_WHITEFLASH_TIME
        self.knockback_vx = knockback_dir * ENEMY_KNOCKBACK_X * BOSS_KNOCKBACK_RESIST
        self.knockback_vy = ENEMY_KNOCKBACK_Y * BOSS_KNOCKBACK_RESIST
        self.on_ground = False
        # Interrupt current attack
        if self.boss_state in ("windup", "charge"):
            self.boss_state = "stun"
            self.boss_timer = BOSS_STUN_TIME * 0.5
            self.vx = 0
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return True

    def render(self, screen, camera):
        if not self.alive:
            return
        screen_rect = camera.apply(self.rect)

        if self.flash_timer > 0:
            color = WHITE
        elif self.boss_state == "windup" and int(self.windup_flash * 15) % 2 == 0:
            color = WHITE
        else:
            color = self.color

        pygame.draw.rect(screen, color, screen_rect)
        # Boss border
        border_color = YELLOW if self.phase == 2 else RED
        pygame.draw.rect(screen, border_color, screen_rect, 3)

        # Face indicator
        eye_x = screen_rect.centerx + 12
        eye_y = screen_rect.top + 20
        pygame.draw.circle(screen, BLACK, (eye_x, eye_y), 5)
        pygame.draw.circle(screen, BLACK, (eye_x - 16, eye_y), 5)

        if self.boss_state == "stun":
            # Stun stars
            pygame.draw.circle(screen, YELLOW,
                               (screen_rect.centerx - 10, screen_rect.top - 10), 6)
            pygame.draw.circle(screen, YELLOW,
                               (screen_rect.centerx + 14, screen_rect.top - 6), 4)
