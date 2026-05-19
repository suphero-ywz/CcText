import pygame
from settings import *


# 160×20 ASCII tile map. G=Ground, P=Platform, B=Background decor, ' '=Air
# Boss arena: columns 135-159
LEVEL_1_DATA = [
    '                                                                                                                                                                ',
    '                                                                                                                                                                ',
    '                    BBB                                             BBB                                                         BBB                             ',
    '                                                                                                                                                                ',
    '                                      BBB                                                                             BBB                                       ',
    '          BBB                                                         BBB                                                                                       ',
    '                      PPP                              PPP                                        PPP                                                           ',
    '                                                                                                                                                                ',
    '                                  PPP                                                           PPP                                                             ',
    '                                                                                                                                                                ',
    '              PPP                               PPP                                  PPP                           PPP                                          ',
    '                                                                                                                                                                ',
    '                              PPP                                   PPP                                  PPP                                                    ',
    '                                                                                                                                                                ',
    '                            BBB                                                 BBB                                               BBB                           ',
    '                                                                                                                                                                ',
    '       GG             GG     GG                          G            GG                             G                                 GG                       ',
    'GGGGGGG  GGGGGGGGGGGGG  GGGGG  GGGGGGGGGGGGGG    GGGGGGGG GGGGGGGGGGGG  GGGGGGGGGGGGGGGGGG    GGGGGGG GGGGGGGG    GGGGGGGGGGGGGGGGGGGGG  GGGGGGGGGGGGGGGGGGGGGGG',
    'GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG',
    'GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG',
]

BOSS_ARENA_START_COL = 135
BOSS_SPAWN_X = 140 * 32  # col 140 * TILE_SIZE
BOSS_SPAWN_Y = 17 * 32   # row 17


class Level:
    def __init__(self, map_data=None):
        if map_data is None:
            map_data = LEVEL_1_DATA
        self.tiles = map_data
        self.rows = len(self.tiles)
        self.cols = len(self.tiles[0]) if self.tiles else 0
        self.width = self.cols * TILE_SIZE
        self.height = self.rows * TILE_SIZE
        self.boss_arena_start = BOSS_ARENA_START_COL * TILE_SIZE
        self.boss_spawn = (BOSS_SPAWN_X, BOSS_SPAWN_Y)

    def get_tile(self, col, row):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.tiles[row][col]
        return None

    def is_solid(self, col, row):
        tile = self.get_tile(col, row)
        return tile in ('G', 'P')

    def get_nearby_tile_rects(self, entity_rect):
        """Return list of pygame.Rect for solid tiles near the entity."""
        margin = 2
        left = max(0, (entity_rect.left - margin) // TILE_SIZE)
        right = min(self.cols - 1, (entity_rect.right + margin) // TILE_SIZE)
        top = max(0, (entity_rect.top - margin) // TILE_SIZE)
        bottom = min(self.rows - 1, (entity_rect.bottom + margin) // TILE_SIZE)

        rects = []
        for row in range(top, bottom + 1):
            for col in range(left, right + 1):
                if self.is_solid(col, row):
                    rects.append(pygame.Rect(
                        col * TILE_SIZE, row * TILE_SIZE,
                        TILE_SIZE, TILE_SIZE
                    ))
        return rects

    def clamp_to_bounds(self, entity):
        """Keep entity within level pixel boundaries."""
        if entity.rect.left < 0:
            entity.rect.left = 0
            entity.vx = 0
        if entity.rect.right > self.width:
            entity.rect.right = self.width
            entity.vx = 0
        if entity.rect.top < 0:
            entity.rect.top = 0
            entity.vy = 0

    def resolve_collision_x(self, entity, dx):
        """Resolve horizontal collisions. Call after moving rect.x only."""
        for tile_rect in self.get_nearby_tile_rects(entity.rect):
            if not entity.rect.colliderect(tile_rect):
                continue
            if dx > 0:
                entity.rect.right = tile_rect.left
            elif dx < 0:
                entity.rect.left = tile_rect.right
            entity.vx = 0
        self.clamp_to_bounds(entity)

    def resolve_collision_y(self, entity, dy):
        """Resolve vertical collisions. Call after moving rect.y only."""
        entity.on_ground = False
        for tile_rect in self.get_nearby_tile_rects(entity.rect):
            if not entity.rect.colliderect(tile_rect):
                continue
            if dy > 0:
                entity.rect.bottom = tile_rect.top
                entity.on_ground = True
            elif dy < 0:
                entity.rect.top = tile_rect.bottom
            entity.vy = 0

        # Grounding snap for exact tile-edge landings
        if not entity.on_ground and dy >= 0 and entity.vy >= 0:
            foot_rect = pygame.Rect(
                entity.rect.left + 2, entity.rect.bottom - 1,
                entity.rect.width - 4, 3
            )
            for tile_rect in self.get_nearby_tile_rects(entity.rect):
                if foot_rect.colliderect(tile_rect):
                    entity.rect.bottom = tile_rect.top
                    entity.on_ground = True
                    entity.vy = 0
                    break

    def render(self, screen, camera):
        start_col = max(0, int(camera.offset_x) // TILE_SIZE)
        end_col = min(self.cols, (int(camera.offset_x) + SCREEN_WIDTH) // TILE_SIZE + 1)
        start_row = max(0, int(camera.offset_y) // TILE_SIZE)
        end_row = min(self.rows, (int(camera.offset_y) + SCREEN_HEIGHT) // TILE_SIZE + 1)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile = self.tiles[row][col]
                if tile == ' ':
                    continue
                x = col * TILE_SIZE - int(camera.offset_x)
                y = row * TILE_SIZE - int(camera.offset_y)

                if tile == 'G':
                    color = DARK_GRAY
                elif tile == 'P':
                    color = MID_GRAY
                elif tile == 'B':
                    color = BG_DECOR_COLOR
                else:
                    continue

                pygame.draw.rect(screen, color, (x, y, TILE_SIZE, TILE_SIZE))
