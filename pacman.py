import pygame
import random
import os
import io
import sys # sys 모듈 추가 (Quit 기능에 사용)
import requests
from math import sqrt, cos, sin
from collections import deque

# 이 스크립트 파일(pacman.py)의 실제 위치를 찾습니다.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 스크립트 위치를 기준으로 'res' 폴더의 절대 경로를 만듭니다.
RES_DIR = os.path.join(SCRIPT_DIR, 'res')

# --- 기본 상수 정의 ---
TILE_WIDTH, TILE_HEIGHT = 24, 24
SCREEN_WIDTH_TILES, SCREEN_HEIGHT_TILES = 19, 22
SCREEN_WIDTH, SCREEN_HEIGHT = SCREEN_WIDTH_TILES * TILE_WIDTH, SCREEN_HEIGHT_TILES * TILE_HEIGHT

# 색상
BLACK, WHITE, BLUE, YELLOW, RED, PINK, CYAN, ORANGE = (0,0,0), (255,255,255), (0,0,255), (255,255,0), (255,0,0), (255,184,222), (0,255,255), (255,184,82)
BUTTON_COLOR, BUTTON_TEXT_COLOR, BUTTON_HOVER_COLOR = (0, 100, 200), (255, 255, 255), (0, 150, 255) # 버튼 색상 추가

# 게임 상태
STATE_PLAYING, STATE_GAME_OVER, STATE_WIN, STATE_PAUSED = 1, 2, 3, 4

# 고스트 상태
GHOST_STATE_CHASE, GHOST_STATE_SCATTER, GHOST_STATE_FRIGHTENED, GHOST_STATE_EATEN, GHOST_STATE_IN_HOUSE, GHOST_STATE_EXITING = 1, 2, 3, 4, 5, 6

# 게임 밸런스 상수
PACMAN_SPEED = 2.0
GHOST_BASE_SPEED = 2.1
GHOST_FRIGHTENED_SPEED = 1.2
GHOST_EATEN_SPEED = 4.0
CRUISE_ELROY_PELLET_COUNT = 20
BLINKY_RAGE_SPEED = 2.1

LEVEL_DATA = '''
107 100 100 100 100 100 100 100 100 133 100 100 100 100 100 100 100 100 108
101 2 2 2 2 2 2 2 2 101 2 2 2 2 2 2 2 2 101
101 2 107 108 2 107 133 108 2 101 2 107 133 108 2 107 108 2 101
101 3 105 106 2 105 130 106 2 110 2 105 130 106 2 105 106 3 101
101 2 2 2 2 2 2 2 2 3 2 2 2 2 2 2 2 2 101
101 2 111 112 2 113 0 111 100 133 100 112 0 113 2 111 112 2 101
101 2 2 2 2 101 0 0 0 101 0 0 0 101 2 2 2 2 101
105 100 100 108 2 131 100 112 0 110 0 111 100 132 2 107 100 100 106
21 0 0 101 2 101 0 0 0 10 0 0 0 101 2 101 0 0 21
111 100 100 106 2 110 0 107 112 1 111 108 0 110 2 105 100 100 112
0 0 0 0 2 0 0 101 11 12 13 101 0 0 2 0 0 0 0
111 100 100 108 2 113 0 105 100 100 100 106 0 113 2 107 100 100 112
0 0 0 101 2 101 0 0 0 0 0 0 0 101 2 101 0 0 0
107 100 100 106 2 110 0 111 100 133 100 112 0 110 2 105 100 100 108
101 2 2 2 2 2 2 2 2 101 2 2 2 2 2 2 2 2 101
101 2 111 108 2 111 100 112 0 110 0 111 100 112 2 107 112 2 101
101 3 2 101 2 2 2 2 2 4 2 2 2 2 2 101 2 3 101
131 112 2 110 2 113 2 111 100 133 100 112 2 113 2 110 2 111 132
101 2 2 2 2 101 2 2 2 101 2 2 2 101 2 2 2 2 101
101 2 111 100 100 130 100 112 2 110 2 111 100 130 100 100 112 2 101
101 2 2 2 2 2 2 2 2 3 2 2 2 2 2 2 2 2 101
105 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 100 106
'''


def load_image_from_pokeapi(pokemon_name):
    try:
        api_url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name.lower()}"
        response = requests.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        image_url = data['sprites']['other']['official-artwork']['front_default']

        if not image_url:
            print(f"Warning: No official artwork found for '{pokemon_name}'.")
            return None

        image_response = requests.get(image_url)
        image_response.raise_for_status()
        image_data = image_response.content

        image_file = io.BytesIO(image_data)
        pygame_image = pygame.image.load(image_file).convert_alpha()
        
        print(f"Successfully loaded '{pokemon_name}' sprite from PokeAPI.")
        return pygame_image

    except (requests.exceptions.RequestException, KeyError, IndexError, TypeError) as e:
        print(f"Warning: Failed to load sprite for '{pokemon_name}' from PokeAPI. Error: {e}")
        return None

class Vector2:
    def __init__(self, x=0, y=0): self.x, self.y = int(x), int(y)
    def __add__(self, o): return Vector2(self.x + o.x, self.y + o.y)
    def __sub__(self, o): return Vector2(self.x - o.x, self.y - o.y)
    def __mul__(self, s): return Vector2(self.x * s, self.y * s)
    def __rmul__(self, s): return Vector2(self.x * s, self.y * s)
    def magnitude(self): return sqrt(self.x**2 + self.y**2)
    def __eq__(self, o): return self.x == o.x and self.y == o.y
    def __hash__(self): return hash((self.x, self.y))

def get_tile_center(tile_pos): return Vector2(tile_pos.x * TILE_WIDTH + TILE_WIDTH/2, tile_pos.y * TILE_HEIGHT + TILE_HEIGHT/2)

def find_shortest_path_bfs(start_pos, end_pos, level):
    queue = deque([([start_pos], start_pos)])
    visited = {start_pos}
    while queue:
        path, current_pos = queue.popleft()
        if current_pos == end_pos: return path
        for d in [Vector2(0,-1), Vector2(0,1), Vector2(-1,0), Vector2(1,0)]:
            next_pos = current_pos + d
            if next_pos not in visited and not level.is_wall(next_pos):
                visited.add(next_pos)
                new_path = list(path)
                new_path.append(next_pos)
                queue.append((new_path, next_pos))
    return None


class Level:
    def __init__(self):
        self.original_map_data = LEVEL_DATA.strip()
        self.map, self.ghost_start_pos, self.wall_tiles = [], {}, []
        self.pacman_start_pos, self.ghost_house_exit, self.pellet_count = Vector2(), Vector2(), 0
        self.total_pellets = 0
        self.load_level()

    def load_level(self):
        self.map, self.ghost_start_pos, self.wall_tiles = [], {}, []
        self.pellet_count = 0
        self.total_pellets = 0
        for y, line in enumerate(self.original_map_data.splitlines()):
            row = []
            for x, tile_val in enumerate(line.strip().split()):
                tile = int(tile_val)
                row.append(tile)
                if tile >= 100: self.wall_tiles.append(Vector2(x, y))
                elif tile == 2 or tile == 3:
                    self.pellet_count += 1
                    self.total_pellets += 1
                elif tile == 4: self.pacman_start_pos = Vector2(x, y)
                elif 10 <= tile <= 13: self.ghost_start_pos[tile - 10] = Vector2(x, y)
                elif tile == 1: self.ghost_house_exit = Vector2(x, y - 1)
            self.map.append(row)

    def get_tile(self, pos): return self.map[int(pos.y)][int(pos.x)] if 0<=pos.y<SCREEN_HEIGHT_TILES and 0<=pos.x<SCREEN_WIDTH_TILES else -1
    def is_wall(self, pos): return self.get_tile(pos) >= 100
    def eat_pellet(self, pos):
        tile_val = self.get_tile(pos)
        if tile_val in [2, 3]:
            self.pellet_count -= 1
            self.map[int(pos.y)][int(pos.x)] = 0
            return tile_val
        return 0

    def draw(self, screen):
        for y in range(SCREEN_HEIGHT_TILES):
            for x in range(SCREEN_WIDTH_TILES):
                tile = self.get_tile(Vector2(x, y))
                if tile >= 100: pygame.draw.rect(screen, BLUE, (x*TILE_WIDTH, y*TILE_HEIGHT, TILE_WIDTH, TILE_HEIGHT), 1)
                elif tile == 2: pygame.draw.circle(screen, WHITE, (int(x*TILE_WIDTH+TILE_WIDTH/2), int(y*TILE_HEIGHT+TILE_HEIGHT/2)), 2)
                elif tile == 3: pygame.draw.circle(screen, WHITE, (int(x*TILE_WIDTH+TILE_WIDTH/2), int(y*TILE_HEIGHT+TILE_HEIGHT/2)), 6)

class Entity:
    def __init__(self, level, start_pos):
        self.level, self.start_pos = level, start_pos
        self.tile_pos, self.pixel_pos = Vector2(start_pos.x, start_pos.y), get_tile_center(start_pos)
        self.direction, self.speed = Vector2(0, 0), 2

    def update(self):
        if self.pixel_pos == get_tile_center(self.tile_pos):
            if not self.level.is_wall(self.tile_pos + self.direction): self.pixel_pos += self.direction * self.speed
            else: self.direction = Vector2(0,0)
        else: self.pixel_pos += self.direction * self.speed
        if (self.direction.x>0 and self.pixel_pos.x>=get_tile_center(self.tile_pos+Vector2(1,0)).x) or \
           (self.direction.x<0 and self.pixel_pos.x<=get_tile_center(self.tile_pos+Vector2(-1,0)).x) or \
           (self.direction.y>0 and self.pixel_pos.y>=get_tile_center(self.tile_pos+Vector2(0,1)).y) or \
           (self.direction.y<0 and self.pixel_pos.y<=get_tile_center(self.tile_pos+Vector2(0,-1)).y):
            self.tile_pos += self.direction; self.pixel_pos = get_tile_center(self.tile_pos)
        if self.pixel_pos.x < 0: self.pixel_pos.x, self.tile_pos.x = SCREEN_WIDTH-1, SCREEN_WIDTH_TILES-1
        elif self.pixel_pos.x > SCREEN_WIDTH: self.pixel_pos.x, self.tile_pos.x = 1, 0

    def draw(self, screen, color): pygame.draw.circle(screen, color, (int(self.pixel_pos.x), int(self.pixel_pos.y)), int(TILE_WIDTH/2)-2)
    def reset(self): self.tile_pos, self.pixel_pos, self.direction = Vector2(self.start_pos.x, self.start_pos.y), get_tile_center(self.start_pos), Vector2(0,0)

class Pacman(Entity):
    def __init__(self, level, start_pos):
        super().__init__(level, start_pos)
        self.buffered_direction, self.lives, self.score, self.bonus_life_awarded, self.speed = Vector2(0,0), 3, 0, False, PACMAN_SPEED
        self.last_direction = Vector2(-1, 0)
        self.anim_frame = 0
        self.anim_timer = 0
        self.animations = {}

        try:
            path1 = os.path.join(RES_DIR, 'pacman_1.png')
            path2 = os.path.join(RES_DIR, 'pacman_2.png')

            pacman_open_orig = pygame.image.load(path1).convert_alpha()
            pacman_closed_orig = pygame.image.load(path2).convert_alpha()

            pacman_open = pygame.transform.scale(pacman_open_orig, (TILE_WIDTH, TILE_HEIGHT))
            pacman_closed = pygame.transform.scale(pacman_closed_orig, (TILE_WIDTH, TILE_HEIGHT))

            self.animations[Vector2(-1, 0)] = [pacman_open, pacman_closed]
            
            right_open = pygame.transform.flip(pacman_open, True, False)
            right_closed = pygame.transform.flip(pacman_closed, True, False)
            self.animations[Vector2(1, 0)] = [right_open, right_closed]

            up_open = pygame.transform.rotate(right_open, 90)
            up_closed = pygame.transform.rotate(right_closed, 90)
            self.animations[Vector2(0, -1)] = [up_open, up_closed]

            down_open = pygame.transform.rotate(right_open, -90)
            down_closed = pygame.transform.rotate(right_closed, -90)
            self.animations[Vector2(0, 1)] = [down_open, down_closed]
            
            self.image = self.animations[self.last_direction][self.anim_frame]

        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load Pac-Man images. Using fallback. Error: {e}")
            self.animations = None
            self.image = None

    def update(self):
        if self.pixel_pos == get_tile_center(self.tile_pos):
            if not self.level.is_wall(self.tile_pos + self.buffered_direction):
                self.direction = self.buffered_direction
        
        if self.direction != Vector2(0, 0):
            self.last_direction = self.direction
            self.anim_timer += 1
            if self.anim_timer >= 5:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 2
        else:
            self.anim_frame = 0
            self.anim_timer = 0

        if self.animations:
            self.image = self.animations[self.last_direction][self.anim_frame]

        super().update()
        if not self.bonus_life_awarded and self.score >= 1500:
            self.lives, self.bonus_life_awarded = self.lives + 1, True

    def set_direction(self, new_dir): self.buffered_direction = new_dir

    def draw(self, screen):
        if self.image:
            rect = self.image.get_rect()
            rect.center = (int(self.pixel_pos.x), int(self.pixel_pos.y))
            screen.blit(self.image, rect)
        else:
            super().draw(screen, YELLOW)

    def reset(self):
        super().reset()
        self.buffered_direction = Vector2(0,0)
        self.last_direction = Vector2(-1, 0)
        self.anim_frame = 0
        self.anim_timer = 0
        if self.animations:
            self.image = self.animations[self.last_direction][self.anim_frame]

class Fruit:
    def __init__(self, position, image=None):
        self.position = position
        self.is_active = False
        self.spawn_time = 0
        self.image = image

    def activate(self, pos=None):
        if pos: self.position = pos
        self.is_active = True
        self.spawn_time = pygame.time.get_ticks()

    def draw(self, screen):
        if self.is_active:
            if self.image:
                center_pos = get_tile_center(self.position)
                rect = self.image.get_rect()
                rect.center = (center_pos.x, center_pos.y)
                screen.blit(self.image, rect)
            else:
                center = get_tile_center(self.position)
                pygame.draw.circle(screen, RED, (int(center.x), int(center.y)), 8)

class Ghost(Entity):
    def __init__(self, level, start_pos, color, ghost_id):
        super().__init__(level, start_pos)
        self.color, self.id, self.state = color, ghost_id, GHOST_STATE_IN_HOUSE
        self.base_speed = GHOST_BASE_SPEED
        self.speed = self.base_speed
        self.scatter_target = Vector2()
        self.calculated_path, self.path_index = None, 0
        self.is_immune = False
        self.in_house_timer = 0

    def update(self, pacman, blinky=None, game_controller=None):
        # FIXED: ghost speed bug - 유령이 집에 도착하면 속도를 기본으로 리셋
        if self.state == GHOST_STATE_EATEN and self.tile_pos == self.start_pos:
            self.state = GHOST_STATE_IN_HOUSE
            self.calculated_path = None
            self.speed = self.base_speed 

        if self.pixel_pos == get_tile_center(self.tile_pos):
            valid_dirs = self.get_valid_directions()
            if self.direction * -1 in valid_dirs and len(valid_dirs) > 1: valid_dirs.remove(self.direction * -1)

            if self.state == GHOST_STATE_FRIGHTENED:
                self.direction = random.choice(valid_dirs) if valid_dirs else self.direction
            elif self.state == GHOST_STATE_EATEN:
                if self.calculated_path and self.path_index < len(self.calculated_path):
                    next_tile = self.calculated_path[self.path_index]
                    self.direction = next_tile - self.tile_pos; self.path_index += 1
                else: self.direction = Vector2(0, 0)
            elif self.state in [GHOST_STATE_CHASE, GHOST_STATE_SCATTER, GHOST_STATE_EXITING]:
                target_tile = self.get_target_tile(pacman, blinky)
                if target_tile and valid_dirs:
                    best_dir = None; min_dist = float('inf')
                    priority_order = [Vector2(0, -1), Vector2(-1, 0), Vector2(0, 1), Vector2(1, 0)]
                    for direction in priority_order:
                        if direction in valid_dirs:
                            dist = (self.tile_pos + direction - target_tile).magnitude()
                            if dist < min_dist: min_dist = dist; best_dir = direction
                    self.direction = best_dir
            elif self.state == GHOST_STATE_IN_HOUSE: self.direction = Vector2(0,0)

        super().update()

    def get_target_tile(self, pacman, blinky):
        if self.state == GHOST_STATE_SCATTER: return self.scatter_target
        elif self.state == GHOST_STATE_CHASE: return self.get_chase_target(pacman, blinky)
        elif self.state == GHOST_STATE_EXITING: return self.level.ghost_house_exit
        return pacman.tile_pos

    def get_valid_directions(self):
        valid_dirs = []
        for d in [Vector2(0,-1), Vector2(0,1), Vector2(-1,0), Vector2(1,0)]:
            if not self.level.is_wall(self.tile_pos + d): valid_dirs.append(d)
        return valid_dirs

    def draw(self, screen, game_controller=None):
        image_to_draw = self.image

        if game_controller and game_controller.ghost_images:
            if self.state == GHOST_STATE_FRIGHTENED:
                if game_controller.frightened_timer < 120 and (game_controller.frightened_timer // 15) % 2 == 0:
                    image_to_draw = game_controller.ghost_images['frightened_flash']
                else:
                    image_to_draw = game_controller.ghost_images['frightened']
            elif self.state == GHOST_STATE_EATEN:
                image_to_draw = game_controller.ghost_images['eyes']

        if image_to_draw:
            rect = image_to_draw.get_rect()
            rect.center = (int(self.pixel_pos.x), int(self.pixel_pos.y))
            screen.blit(image_to_draw, rect)
        else:
            draw_color = self.color
            if self.state == GHOST_STATE_FRIGHTENED:
                draw_color = BLUE
            elif self.state == GHOST_STATE_EATEN:
                draw_color = WHITE
            super().draw(screen, draw_color)

    def get_chase_target(self, pacman, blinky): return pacman.tile_pos
    def reset(self):
        super().reset()
        self.state, self.speed, self.calculated_path, self.is_immune = GHOST_STATE_IN_HOUSE, self.base_speed, None, False
        self.in_house_timer = 0

class Blinky(Ghost):
    def __init__(self, level, start_pos):
        super().__init__(level, start_pos, RED, 0)
        self.scatter_target = Vector2(SCREEN_WIDTH_TILES - 2, 1)
        self.rage_speed = BLINKY_RAGE_SPEED
        try:
            blinky_img = pygame.image.load(os.path.join(RES_DIR, 'blinky.png')).convert_alpha()
            self.image = pygame.transform.scale(blinky_img, (TILE_WIDTH, TILE_HEIGHT))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load blinky.png. Error: {e}")
            self.image = None

    def update(self, pacman, blinky=None, game_controller=None):
        if self.state not in [GHOST_STATE_FRIGHTENED, GHOST_STATE_EATEN]:
            if game_controller and game_controller.level.total_pellets > 0:
                pellets_eaten_ratio = (game_controller.level.total_pellets - game_controller.level.pellet_count) / game_controller.level.total_pellets
                self.speed = self.base_speed + (self.rage_speed - self.base_speed) * pellets_eaten_ratio
            else:
                self.speed = self.base_speed
        
        super().update(pacman, blinky, game_controller)

    def get_chase_target(self, pacman, blinky=None): return pacman.tile_pos

class Pinky(Ghost):
    def __init__(self, level, start_pos):
        super().__init__(level, start_pos, PINK, 1)
        self.scatter_target = Vector2(1, 1)
        try:
            pinky_img = pygame.image.load(os.path.join(RES_DIR, 'pinky.png')).convert_alpha()
            self.image = pygame.transform.scale(pinky_img, (TILE_WIDTH, TILE_HEIGHT))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load pinky.png. Error: {e}")
            self.image = None
    def get_chase_target(self, pacman, blinky=None):
        target = pacman.tile_pos + pacman.direction * 4
        if pacman.direction == Vector2(0, -1): target = pacman.tile_pos + Vector2(-4, -4)
        return target

class Inky(Ghost):
    def __init__(self, level, start_pos):
        super().__init__(level, start_pos, CYAN, 2)
        self.scatter_target = Vector2(SCREEN_WIDTH_TILES - 2, SCREEN_HEIGHT_TILES - 2)
        try:
            inky_img = pygame.image.load(os.path.join(RES_DIR, 'inky.png')).convert_alpha()
            self.image = pygame.transform.scale(inky_img, (TILE_WIDTH, TILE_HEIGHT))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load inky.png. Error: {e}")
            self.image = None
    def get_chase_target(self, pacman, blinky):
        if not blinky: return pacman.tile_pos
        pivot = pacman.tile_pos + pacman.direction * 2
        return pivot + (pivot - blinky.tile_pos)

class Clyde(Ghost):
    def __init__(self, level, start_pos):
        super().__init__(level, start_pos, ORANGE, 3)
        self.scatter_target = Vector2(1, SCREEN_HEIGHT_TILES - 2)
        try:
            clyde_img = pygame.image.load(os.path.join(RES_DIR, 'clyde.png')).convert_alpha()
            self.image = pygame.transform.scale(clyde_img, (TILE_WIDTH, TILE_HEIGHT))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load clyde.png. Error: {e}")
            self.image = None
    def get_chase_target(self, pacman, blinky=None):
        return pacman.tile_pos if (self.tile_pos - pacman.tile_pos).magnitude() > 8 else self.scatter_target

class GameController:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pacman")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        
        self.init_game()

    def init_game(self):
        self.state = STATE_PLAYING
        self.level = Level()
        self.level.load_level()
        
        self.round_level = 1
        
        self.ghost_images = {}
        try:
            frightened_img = pygame.image.load(os.path.join(RES_DIR, 'frightened.png')).convert_alpha()
            frightened_flash_img = pygame.image.load(os.path.join(RES_DIR, 'frightened_flash.png')).convert_alpha()
            eyes_img = pygame.image.load(os.path.join(RES_DIR, 'eyes.png')).convert_alpha()
            
            self.ghost_images['frightened'] = pygame.transform.scale(frightened_img, (TILE_WIDTH, TILE_HEIGHT))
            self.ghost_images['frightened_flash'] = pygame.transform.scale(frightened_flash_img, (TILE_WIDTH, TILE_HEIGHT))
            self.ghost_images['eyes'] = pygame.transform.scale(eyes_img, (TILE_WIDTH, TILE_HEIGHT))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load common ghost images. Game may not display correctly. Error: {e}")
            self.ghost_images = None

        self.pacman = Pacman(self.level, self.level.pacman_start_pos)
        self.pacman.score = 0
        self.pacman.lives = 3
        self.pacman.bonus_life_awarded = False

        self.ghosts = [Blinky(self.level, self.level.ghost_start_pos[0]), Pinky(self.level, self.level.ghost_start_pos[1]), Inky(self.level, self.level.ghost_start_pos[2]), Clyde(self.level, self.level.ghost_start_pos[3])]
        self.blinky = self.ghosts[0]
        
        self.increase_difficulty()

        self.frightened_timer, self.scatter_chase_timer, self.current_wave, self.ghost_eaten_score = 0, 0, 0, 200
        self.ghost_mode = GHOST_STATE_SCATTER
        
        self.fruit_images = []
        fruit_pokemon_names = ['cherubi', 'bounsweet', 'applin']
        for name in fruit_pokemon_names:
            img = load_image_from_pokeapi(name)
            if img:
                scaled_img = pygame.transform.scale(img, (TILE_WIDTH, TILE_HEIGHT))
                self.fruit_images.append(scaled_img)

        self.fruit = Fruit(Vector2(9, 13), None)
        self.fruit_spawn_level = 0
        
        self.state = STATE_PAUSED
        self.pause_timer = 60

    def increase_difficulty(self):
        # NEW: 최고 속도 제한 추가
        max_ghost_speed = PACMAN_SPEED + 0.8
        max_rage_speed = PACMAN_SPEED + 1.1

        speed_increase = 0.15 * (self.round_level - 1)
        rage_speed_increase = 0.2 * (self.round_level - 1)
        for ghost in self.ghosts:
            ghost.base_speed = min(GHOST_BASE_SPEED + speed_increase, max_ghost_speed)
            if isinstance(ghost, Blinky):
                ghost.rage_speed = min(BLINKY_RAGE_SPEED + rage_speed_increase, max_rage_speed)

    def init_round(self):
        self.level.load_level()
        self.pacman.reset()
        for ghost in self.ghosts:
            ghost.reset()
        
        self.fruit.is_active = False
        self.fruit_spawn_level = 0

        self.state = STATE_PAUSED
        self.pause_timer = 120

    def start_new_round(self):
        self.round_level += 1
        self.increase_difficulty()
        self.init_round()

    def check_all_pellets_eaten(self):
        return self.level.pellet_count <= 0

    def reset_after_death(self):
        self.pacman.reset()
        for ghost in self.ghosts: ghost.reset()
        self.state, self.pause_timer = STATE_PAUSED, 60

    def update(self):
        if self.state == STATE_PLAYING:
            self.pacman.update()
            self.handle_pellet_eating()
            self.update_ghosts()
            self.handle_fruit_events()
            self.check_collisions()
            
            if self.check_all_pellets_eaten():
                self.start_new_round()

        elif self.state == STATE_PAUSED:
            self.pause_timer -= 1
            if self.pause_timer <= 0:
                self.state = STATE_PLAYING
    
    def handle_pellet_eating(self):
        eaten_val = self.level.eat_pellet(self.pacman.tile_pos)
        if eaten_val in [2, 3]:
            if eaten_val == 2: self.pacman.score += 10
            elif eaten_val == 3:
                self.pacman.score += 50
                for g in self.ghosts: g.is_immune = False
                self.frighten_ghosts()
                self.ghost_eaten_score = 200
            
            pellets_eaten = self.level.total_pellets - self.level.pellet_count

            if self.fruit_spawn_level == 0 and pellets_eaten >= 10:
                if self.fruit_images:
                    self.fruit.image = random.choice(self.fruit_images)
                self.fruit.activate(Vector2(9, 12))
                self.fruit_spawn_level = 1
            elif self.fruit_spawn_level == 1 and pellets_eaten >= 70:
                if self.fruit_images:
                    self.fruit.image = random.choice(self.fruit_images)
                self.fruit.activate(Vector2(9, 12))
                self.fruit_spawn_level = 2
    
    def handle_fruit_events(self):
        if self.fruit.is_active:
            if pygame.time.get_ticks() - self.fruit.spawn_time > 10000:
                self.fruit.is_active = False
            elif self.pacman.tile_pos == self.fruit.position:
                self.pacman.score += 100
                self.fruit.is_active = False

    def frighten_ghosts(self):
        self.frightened_timer = 7 * 60
        for g in self.ghosts:
            if g.state != GHOST_STATE_EATEN:
                g.state = GHOST_STATE_FRIGHTENED
                g.speed = GHOST_FRIGHTENED_SPEED

    def update_ghosts(self):
        for ghost in self.ghosts:
            if ghost.state == GHOST_STATE_IN_HOUSE:
                ghost.in_house_timer += 1
                exit_condition = False
                if ghost.id == 0: exit_condition = ghost.in_house_timer >= 1
                elif ghost.id == 1: exit_condition = ghost.in_house_timer >= 4 * 60
                elif ghost.id == 2: exit_condition = ghost.in_house_timer >= 8 * 60
                elif ghost.id == 3: exit_condition = ghost.in_house_timer >= 12 * 60
                
                if exit_condition:
                    ghost.state = GHOST_STATE_EXITING

            # FIXED: ghost speed bug - 집에서 나올 때 속도를 리셋
            if ghost.state == GHOST_STATE_EXITING and ghost.tile_pos == self.level.ghost_house_exit:
                if self.frightened_timer > 0 and not ghost.is_immune:
                    ghost.state, ghost.speed = GHOST_STATE_FRIGHTENED, GHOST_FRIGHTENED_SPEED
                else:
                    ghost.state = self.ghost_mode
                    ghost.speed = ghost.base_speed

        if self.frightened_timer > 0:
            self.frightened_timer -= 1
            if self.frightened_timer == 0:
                # FIXED: ghost speed bug - Frightened 상태가 끝나면 속도를 리셋
                for g in self.ghosts: 
                    if g.state == GHOST_STATE_FRIGHTENED:
                        g.state = self.ghost_mode
                        g.speed = g.base_speed
        else:
            self.scatter_chase_timer += 1
            waves = [(7*60, 20*60), (7*60, 20*60), (5*60, 20*60), (float('inf'), 5*60)]
            if self.current_wave < len(waves):
                scatter_time, chase_time = waves[self.current_wave]
                if (self.ghost_mode == GHOST_STATE_SCATTER and self.scatter_chase_timer >= scatter_time) or \
                   (self.ghost_mode == GHOST_STATE_CHASE and self.scatter_chase_timer >= chase_time):
                    self.ghost_mode = GHOST_STATE_CHASE if self.ghost_mode == GHOST_STATE_SCATTER else GHOST_STATE_SCATTER
                    self.scatter_chase_timer = 0
                    if self.ghost_mode == GHOST_STATE_SCATTER: self.current_wave += 1

        for ghost in self.ghosts:
            if ghost.state not in [GHOST_STATE_FRIGHTENED, GHOST_STATE_EATEN, GHOST_STATE_IN_HOUSE, GHOST_STATE_EXITING]:
                ghost.state = self.ghost_mode
            ghost.update(self.pacman, self.blinky, self)

    def check_collisions(self):
        pacman_died = False
        for ghost in self.ghosts:
            if (self.pacman.pixel_pos - ghost.pixel_pos).magnitude() < TILE_WIDTH * 0.75:
                if ghost.state == GHOST_STATE_FRIGHTENED:
                    ghost.is_immune = True
                    ghost.state, ghost.speed = GHOST_STATE_EATEN, GHOST_EATEN_SPEED
                    self.pacman.score += self.ghost_eaten_score; self.ghost_eaten_score *= 2
                    path_to_nest = find_shortest_path_bfs(ghost.tile_pos, ghost.start_pos, self.level)
                    if path_to_nest: ghost.calculated_path, ghost.path_index = path_to_nest, 1
                elif ghost.state not in [GHOST_STATE_EATEN, GHOST_STATE_IN_HOUSE]:
                    pacman_died = True
        
        if pacman_died:
            self.pacman.lives -= 1
            if self.pacman.lives > 0:
                self.reset_after_death()
            else:
                self.pacman.lives = 0
                self.state = STATE_GAME_OVER

    def draw(self):
        self.screen.fill(BLACK)
        if self.state == STATE_PLAYING or self.state == STATE_PAUSED:
            self.level.draw(self.screen)
            self.pacman.draw(self.screen)
            self.fruit.draw(self.screen)
            for ghost in self.ghosts:
                ghost.draw(self.screen, self)
            self.draw_ui()
        
        pygame.display.flip()

    def draw_ui(self):
        self.screen.blit(self.font.render(f"Score: {self.pacman.score}", True, WHITE), (10, 10))
        self.screen.blit(self.font.render(f"Round: {self.round_level}", True, WHITE), (SCREEN_WIDTH // 2 - 60, 10))
        self.screen.blit(self.font.render(f"Lives: {self.pacman.lives}", True, WHITE), (SCREEN_WIDTH - 120, 10))

    def game_over_loop(self):
        button_width, button_height = 120, 50
        retry_button_rect = pygame.Rect(SCREEN_WIDTH/2 - button_width - 20, SCREEN_HEIGHT/2 + 50, button_width, button_height)
        quit_button_rect = pygame.Rect(SCREEN_WIDTH/2 + 20, SCREEN_HEIGHT/2 + 50, button_width, button_height)

        while True:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if retry_button_rect.collidepoint(mouse_pos):
                        self.init_game()
                        return
                    if quit_button_rect.collidepoint(mouse_pos):
                        pygame.quit()
                        sys.exit()

            self.screen.fill(BLACK)
            
            title_text = self.font.render("Game Over", True, YELLOW)
            self.screen.blit(title_text, title_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50)))

            score_text = self.small_font.render(f"Final Score: {self.pacman.score}", True, WHITE)
            self.screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)))

            retry_color = BUTTON_HOVER_COLOR if retry_button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
            pygame.draw.rect(self.screen, retry_color, retry_button_rect, border_radius=10)
            retry_text = self.small_font.render("Retry", True, BUTTON_TEXT_COLOR)
            self.screen.blit(retry_text, retry_text.get_rect(center=retry_button_rect.center))

            quit_color = BUTTON_HOVER_COLOR if quit_button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
            pygame.draw.rect(self.screen, quit_color, quit_button_rect, border_radius=10)
            quit_text = self.small_font.render("Quit", True, BUTTON_TEXT_COLOR)
            self.screen.blit(quit_text, quit_text.get_rect(center=quit_button_rect.center))

            pygame.display.flip()
            self.clock.tick(60)

    def run(self):
        running = True
        while running:
            if self.state == STATE_GAME_OVER:
                self.game_over_loop()
            else: # STATE_PLAYING or STATE_PAUSED
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: running = False
                        elif event.key == pygame.K_LEFT: self.pacman.set_direction(Vector2(-1,0))
                        elif event.key == pygame.K_RIGHT: self.pacman.set_direction(Vector2(1,0))
                        elif event.key == pygame.K_UP: self.pacman.set_direction(Vector2(0,-1))
                        elif event.key == pygame.K_DOWN: self.pacman.set_direction(Vector2(0,1))
                self.update()
                self.draw()

            self.clock.tick(60)
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    game = GameController()
    game.run()