import pygame
import math
import random
import sys
import os
import numpy as np

# Initialize Pygame & Mixer
pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)
try:
    pygame.mixer.init()
    AUDIO_ENABLED = True
except:
    AUDIO_ENABLED = False

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rolling Ball: Roguelite Frontier")
clock = pygame.time.Clock()

# Fonts
font = pygame.font.SysFont("Arial", 36, bold=True)
large_font = pygame.font.SysFont("Arial", 64, bold=True)
small_font = pygame.font.SysFont("Arial", 24, bold=True)
tiny_font = pygame.font.SysFont("Arial", 18, bold=True)

# --- Biomes & Constants ---
BIOMES = [
    {"name": "Grasslands", "sky": (135, 206, 235), "grass": (82, 183, 136), "dirt": (139, 90, 43), "line": (50, 130, 90), "mountain": (100, 140, 160), "decor": (50, 130, 90)},
    {"name": "Desert Dunes", "sky": (237, 197, 63), "grass": (238, 214, 145), "dirt": (194, 154, 108), "line": (180, 140, 90), "mountain": (200, 160, 110), "decor": (180, 140, 90)},
    {"name": "Rocky Mountains", "sky": (150, 150, 180), "grass": (120, 120, 130), "dirt": (80, 80, 90), "line": (60, 60, 70), "mountain": (90, 90, 110), "decor": (60, 60, 70)},
    {"name": "Bumpy Badlands", "sky": (200, 100, 100), "grass": (150, 75, 75), "dirt": (100, 50, 50), "line": (80, 40, 40), "mountain": (120, 60, 60), "decor": (80, 40, 40)}
]

ball_radius = 20
base_gravity = 0.6

# High Score File
HS_FILE = "highscore.txt"
high_score = 0
if os.path.exists(HS_FILE):
    try:
        with open(HS_FILE, "r") as f:
            high_score = int(f.read())
    except:
        high_score = 0

# --- EXPERT ALGORITHM 1: Fractal Value Noise ---
class ValueNoise:
    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randint(0, 9999)
        self.cache = {}
    def smoothstep(self, t): return t * t * (3 - 2 * t)
    def noise_1d(self, x):
        x_int = int(math.floor(x))
        if x_int not in self.cache: self.cache[x_int] = ((x_int * 1234.5678 + self.seed) % 1.0)
        return self.cache[x_int]
    def fractal_noise(self, x, octaves=4):
        total, amplitude, frequency, max_amplitude = 0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            x_freq = x * frequency
            x0, x1 = math.floor(x_freq), math.floor(x_freq) + 1
            t = self.smoothstep(x_freq - x0)
            total += (self.noise_1d(x0) * (1 - t) + self.noise_1d(x1) * t) * amplitude
            max_amplitude += amplitude; amplitude *= 0.5; frequency *= 2.0
        return total / max_amplitude

# --- EXPERT ALGORITHM 2: Catmull-Rom Spline ---
def catmull_rom(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)

def get_hill_spline_y(x, hill_points):
    for i in range(len(hill_points) - 3):
        x1, y1 = hill_points[i+1]; x2, y2 = hill_points[i+2]
        if x1 <= x <= x2:
            t = (x - x1) / (x2 - x1) if x2 != x1 else 0
            return catmull_rom(hill_points[i][1], y1, y2, hill_points[i+3][1], t)
    return HEIGHT

def get_hill_angle(x, hill_points):
    dx = 5
    return math.atan2(get_hill_spline_y(x + dx, hill_points) - get_hill_spline_y(x - dx, hill_points), 2 * dx)

def draw_text(text, font, color, x, y, center=False):
    surface = font.render(text, True, color)
    rect = surface.get_rect()
    if center: rect.center = (x, y)
    else: rect.topleft = (x, y)
    screen.blit(surface, rect)

# --- EXPERT ALGORITHM 3: Procedural Audio Synthesis ---
def generate_sound(freq, dur, vol=0.5, wave_type='sine', sweep=0):
    if not AUDIO_ENABLED: return None
    sample_rate = 44100
    n_samples = int(sample_rate * dur)
    buf = np.zeros((n_samples, 2), dtype=np.int16)
    for i in range(n_samples):
        t = float(i) / sample_rate
        f = freq + (sweep * t)
        if wave_type == 'sine': val = math.sin(2 * math.pi * f * t)
        elif wave_type == 'square': val = 1.0 if math.sin(2 * math.pi * f * t) > 0 else -1.0
        elif wave_type == 'noise': val = random.uniform(-1, 1)
        else: val = 0
        env = 1.0 - (t / dur) ** 2
        val *= env * vol
        buf[i] = (int(val * 32767), int(val * 32767))
    return pygame.sndarray.make_sound(buf)

class AudioEngine:
    def __init__(self):
        if AUDIO_ENABLED:
            self.snd_jump = generate_sound(400, 0.15, 0.4, 'sine', 800)
            self.snd_coin = generate_sound(800, 0.1, 0.4, 'square')
            self.snd_smash = generate_sound(150, 0.2, 0.6, 'noise')
            self.snd_powerup = generate_sound(500, 0.3, 0.5, 'sine', 1000)
            self.snd_boost = generate_sound(200, 0.2, 0.5, 'square', 400)
            self.snd_pound = generate_sound(80, 0.3, 0.8, 'noise')
            self.snd_crash = generate_sound(100, 0.5, 0.8, 'noise')
            self.snd_levelup = generate_sound(600, 0.4, 0.6, 'sine', 1200)
        else:
            self.snd_jump = self.snd_coin = self.snd_smash = self.snd_powerup = self.snd_boost = self.snd_pound = self.snd_crash = self.snd_levelup = None
            
    def play(self, sound):
        if sound: sound.play()

audio = AudioEngine()

# --- EXPERT ALGORITHM 4: Object Pooling ---
class ParticlePool:
    def __init__(self, capacity=600):
        self.pool = []
        for _ in range(capacity):
            self.pool.append({"active": False, "x": 0, "y": 0, "vx": 0, "vy": 0, "color": (0,0,0), "life": 0, "max_life": 0, "size": 0})

    def emit(self, x, y, color, speed_mult=1, count=10):
        emitted = 0
        for p in self.pool:
            if not p["active"]:
                p.update({"active": True, "x": x, "y": y, "color": color, 
                          "vx": random.uniform(-3, 3) * speed_mult, "vy": random.uniform(-4, -1) * speed_mult, 
                          "life": random.randint(20, 40), "max_life": random.randint(20, 40), "size": random.randint(3, 7)})
                emitted += 1
                if emitted >= count: break

    def update_and_draw(self, surface):
        for p in self.pool:
            if p["active"]:
                p["x"] += p["vx"]; p["y"] += p["vy"]; p["vy"] += 0.2; p["life"] -= 1
                if p["life"] <= 0: p["active"] = False
                else:
                    s = int(p["size"] * (p["life"] / p["max_life"]))
                    if s > 0: pygame.draw.circle(surface, p["color"], (int(p["x"]), int(p["y"])), s)

class Coin:
    def __init__(self, x, y): self.x = x; self.y = y; self.radius = 10; self.angle = 0
    def update(self, ss): self.x -= ss; self.angle += 0.15
    def get_rect(self): return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius*2, self.radius*2)
    def draw(self, s):
        w = max(2, abs(math.cos(self.angle)) * self.radius)
        r = pygame.Rect(self.x - w, self.y - self.radius, w*2, self.radius*2)
        pygame.draw.ellipse(s, (255, 215, 0), r); pygame.draw.ellipse(s, (200, 150, 0), r, 2)

class PowerUp:
    def __init__(self, x, y, t): self.x = x; self.y = y; self.type = t; self.radius = 15; self.pulse = 0
    def update(self, ss): self.x -= ss; self.pulse += 0.1
    def get_rect(self): return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius*2, self.radius*2)
    def draw(self, s):
        gs = self.radius + math.sin(self.pulse) * 4
        c1, c2 = ((100, 200, 255), (255, 255, 255)) if self.type == "shield" else ((255, 50, 50), (255, 255, 255))
        pygame.draw.circle(s, c1, (int(self.x), int(self.y)), int(gs)); pygame.draw.circle(s, c2, (int(self.x), int(self.y)), self.radius - 3)

class BoostPad:
    def __init__(self, x, y): self.x = x; self.y = y; self.w = 60; self.h = 15; self.pulse = 0
    def update(self, ss): self.x -= ss; self.pulse += 0.2
    def get_rect(self): return pygame.Rect(self.x, self.y - 5, self.w, self.h)
    def draw(self, s):
        o = math.sin(self.pulse) * 2
        pts = [(self.x, self.y), (self.x+20, self.y-10+o), (self.x+20, self.y-3), (self.x+40, self.y-3), (self.x+40, self.y-10+o), (self.x+60, self.y), (self.x+40, self.y+7-o), (self.x+40, self.y), (self.x+20, self.y), (self.x+20, self.y+7-o)]
        pygame.draw.polygon(s, (255, 255, 0), pts); pygame.draw.polygon(s, (200, 150, 0), pts, 2)

class Obstacle:
    def __init__(self, x, y, t):
        self.x = x; self.y = y; self.type = t; self.timer = 0
        if t == "small_rock": self.w, self.h = 30, 30
        elif t == "tall_rock": self.w, self.h = 25, 50
        elif t == "wide_rock": self.w, self.h = 70, 25
        elif t == "double_rock": self.w, self.h = 80, 30
        elif t == "crate": self.w, self.h = 40, 40
        elif t == "spikes": self.w, self.h = 40, 20
        elif t == "flying_saw": self.w, self.h = 40, 40
    def update(self, ss, time=0): 
        self.x -= ss
        if self.type == "spikes": self.timer += 1
        if self.type == "flying_saw": self.timer += 1
    def get_rect(self): 
        if self.type == "spikes" and 30 < self.timer < 90:
            return pygame.Rect(self.x + 4, self.y + 4, self.w - 8, self.h - 8)
        elif self.type == "flying_saw":
            return pygame.Rect(self.x + 5, self.y + 5, self.w - 10, self.h - 10)
        elif self.type != "spikes":
            return pygame.Rect(self.x + 4, self.y + 4, self.w - 8, self.h - 8)
        return pygame.Rect(0,0,0,0)
    def draw(self, s, by):
        if self.type == "crate":
            c, o = (160, 110, 60), (80, 50, 20)
            r = pygame.Rect(self.x, self.y, self.w, self.h)
            pygame.draw.rect(s, c, r); pygame.draw.rect(s, o, r, 3)
            pygame.draw.line(s, o, (self.x, self.y), (self.x+self.w, self.y+self.h), 3)
            pygame.draw.line(s, o, (self.x+self.w, self.y), (self.x, self.y+self.h), 3)
        elif self.type == "spikes":
            offset = 0
            if self.timer <= 30: offset = (30 - self.timer) / 30 * 20
            elif self.timer > 90: offset = (self.timer - 90) / 30 * 20
            if offset < 20:
                pts1 = [(self.x, by), (self.x+10, self.y+offset), (self.x+20, by)]
                pts2 = [(self.x+20, by), (self.x+30, self.y+offset), (self.x+40, by)]
                pygame.draw.polygon(s, (200, 200, 200), pts1); pygame.draw.polygon(s, (200, 200, 200), pts2)
                pygame.draw.polygon(s, (100, 100, 100), pts1, 2); pygame.draw.polygon(s, (100, 100, 100), pts2, 2)
        elif self.type == "flying_saw":
            # Bobbing motion
            bob_y = self.y + math.sin(self.timer * 0.1) * 15
            cx, cy = self.x + self.w//2, int(bob_y + self.h//2)
            # Sawblade
            pygame.draw.circle(s, (150, 150, 150), (cx, cy), 18)
            pygame.draw.circle(s, (80, 80, 80), (cx, cy), 18, 3)
            # Teeth
            for i in range(8):
                ang = self.timer * 0.3 + (i * math.pi / 4)
                tx = cx + math.cos(ang) * 18
                ty = cy + math.sin(ang) * 18
                pygame.draw.circle(s, (200, 200, 200), (int(tx), int(ty)), 4)
            pygame.draw.circle(s, (50, 50, 50), (cx, cy), 6)
        else:
            c, o = (70, 70, 70), (40, 40, 40)
            if self.type == "small_rock":
                pygame.draw.rect(s, c, (self.x, self.y, self.w, self.h), border_radius=8)
                pygame.draw.rect(s, o, (self.x, self.y, self.w, self.h), 3, border_radius=8)
            elif self.type == "tall_rock":
                pts = [(self.x, by), (self.x+self.w//2, self.y), (self.x+self.w, by)]
                pygame.draw.polygon(s, c, pts); pygame.draw.polygon(s, o, pts, 3)
            elif self.type == "wide_rock":
                pygame.draw.rect(s, c, (self.x, self.y, self.w, self.h), border_radius=12)
                pygame.draw.rect(s, o, (self.x, self.y, self.w, self.h), 3, border_radius=12)
            elif self.type == "double_rock":
                r1, r2 = (self.x, self.y, 30, 30), (self.x+50, self.y, 30, 30)
                pygame.draw.rect(s, c, r1, border_radius=8); pygame.draw.rect(s, c, r2, border_radius=8)
                pygame.draw.rect(s, o, r1, 3, border_radius=8); pygame.draw.rect(s, o, r2, 3, border_radius=8)

def main():
    global high_score
    
    state = "MENU"
    noise_gen = ValueNoise()
    particle_pool = ParticlePool()
    
    score = 0; coins_collected = 0
    scroll_speed = 5; target_scroll_speed = 5
    
    # Player Stats (Roguelite Upgrades)
    stats = {
        "base_speed": 5.0,
        "smash_speed": 8.0,
        "max_jumps": 2,
        "magnet_range": 250,
        "level": 1,
        "xp": 0,
        "xp_needed": 100
    }
    
    shake_intensity = 0; popups = []
    combo_multiplier = 1; combo_timer = 0
    
    flash_color = (0,0,0); flash_alpha = 0
    shockwaves = [] # [x, y, radius, max_radius, color]
    weather_particles = []
    weather_type = "None"
    
    hill_points = []
    current_biome_index = 0
    current_biome = BIOMES[current_biome_index]
    biome_progress = 0; biome_length = random.randint(1500, 3000)
    
    clouds = [[random.randint(0, WIDTH), random.randint(50, 200), random.randint(50, 100)] for _ in range(5)]
    mountain_offset = 0; time_of_day = 0.0; terrain_decor = []
    
    for x in range(-80, WIDTH * 2 + 80, 80):
        y = HEIGHT // 2 + (noise_gen.fractal_noise(x * 0.005) - 0.5) * 100
        hill_points.append([x, y])
        
    ball_x = WIDTH // 4
    ball_y = get_hill_spline_y(ball_x, hill_points) - ball_radius
    ball_vy = 0; on_ground = True; ball_angle = 0; jumps_left = stats["max_jumps"]; space_held = False
    
    has_shield = False; magnet_timer = 0
    is_pounding = False
    trail = []; speed_lines = []

    obstacles = []; coins = []; powerups = []; boost_pads = []
    obstacle_timer = 0; coin_timer = 0; powerup_timer = 0; boost_timer = 0

    # Pre-render Vignette
    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for i in range(5):
        pygame.draw.rect(vignette, (0,0,0, 15), (i*4, i*4, WIDTH-i*8, HEIGHT-i*8), border_radius=15)

    ball_surf = pygame.Surface((ball_radius*2 + 10, ball_radius*2 + 10), pygame.SRCALPHA)
    pygame.draw.circle(ball_surf, (255, 87, 51), (ball_radius+5, ball_radius+5), ball_radius)
    pygame.draw.arc(ball_surf, (180, 40, 20), (5, 5, ball_radius*2, ball_radius*2), math.pi, 2*math.pi, ball_radius)
    pygame.draw.circle(ball_surf, (255, 180, 150), (ball_radius-1, ball_radius-1), ball_radius - 12)
    pygame.draw.line(ball_surf, (255, 255, 255), (5, ball_radius+5), (ball_radius*2+5, ball_radius+5), 3)

    running = True
    while running:
        shake_x, shake_y = 0, 0
        if shake_intensity > 0:
            shake_x = random.randint(-shake_intensity, shake_intensity)
            shake_y = random.randint(-shake_intensity, shake_intensity)
            shake_intensity -= 1

        frame_surface = pygame.Surface((WIDTH, HEIGHT))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.KEYDOWN:
                if state == "MENU" and event.key == pygame.K_RETURN: state = "PLAYING"
                elif state == "GAME_OVER" and event.key == pygame.K_RETURN:
                    state = "PLAYING"
                    score = 0; coins_collected = 0; scroll_speed = 5
                    stats = {"base_speed": 5.0, "smash_speed": 8.0, "max_jumps": 2, "magnet_range": 250, "level": 1, "xp": 0, "xp_needed": 100}
                    hill_points = [[x, HEIGHT // 2] for x in range(-80, WIDTH * 2 + 80, 80)]
                    ball_y = get_hill_spline_y(ball_x, hill_points) - ball_radius
                    ball_vy = 0; obstacles.clear(); coins.clear(); powerups.clear(); boost_pads.clear()
                    current_biome_index = 0; current_biome = BIOMES[0]
                    has_shield = False; magnet_timer = 0; combo_multiplier = 1; is_pounding = False
                if event.key == pygame.K_SPACE:
                    space_held = True
                    if state == "PLAYING" and jumps_left > 0 and not is_pounding:
                        ball_vy = -13; on_ground = False; jumps_left -= 1
                        particle_pool.emit(ball_x, ball_y + ball_radius, current_biome["dirt"], count=5)
                        audio.play(audio.snd_jump)
                if event.key in (pygame.K_DOWN, pygame.K_s) and state == "PLAYING" and not on_ground and not is_pounding:
                    is_pounding = True
                    ball_vy = 20 
                    audio.play(audio.snd_pound)
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    space_held = False
                    if ball_vy < -5: ball_vy = -5 

        if state == "PLAYING":
            steps = max(1, int(scroll_speed / 4))
            sub_step_speed = scroll_speed / steps
            
            for _ in range(steps):
                ground_angle = get_hill_angle(ball_x, hill_points)
                slope_factor = math.sin(ground_angle) * 8 
                
                target_scroll_speed = stats["base_speed"] + slope_factor
                if not on_ground and ball_vy > 0: target_scroll_speed += ball_vy * 0.2
                scroll_speed += (target_scroll_speed - scroll_speed) * 0.1
                scroll_speed = max(3, min(scroll_speed, 16))

                for point in hill_points: point[0] -= sub_step_speed
                biome_progress += sub_step_speed
                
                while hill_points[-1][0] < WIDTH + 100:
                    last_x, last_y = hill_points[-1]
                    new_x = last_x + 80 
                    noise_val = noise_gen.fractal_noise(new_x * 0.005)
                    base_y = HEIGHT // 2; amplitude = 150
                    new_y = base_y + (noise_val - 0.5) * amplitude
                    if current_biome["name"] == "Rocky Mountains": new_y += 50
                    elif current_biome["name"] == "Desert Dunes": new_y -= 20
                    new_y = max(150, min(HEIGHT - 100, new_y))
                    hill_points.append([new_x, new_y])
                    if random.random() < 0.3: terrain_decor.append([new_x, new_y, random.choice(["tuft", "pebble"])])

                hill_points = [p for p in hill_points if p[0] > -100]
                for d in terrain_decor: d[0] -= sub_step_speed
                terrain_decor = [d for d in terrain_decor if d[0] > -50]

                ball_vy += (base_gravity * 2 if is_pounding else base_gravity) / steps
                ball_y += ball_vy / steps

                gy = get_hill_spline_y(ball_x, hill_points)
                if ball_y + ball_radius >= gy:
                    ball_y = gy - ball_radius
                    if not on_ground:
                        if is_pounding:
                            is_pounding = False
                            shake_intensity = 15
                            flash_color = (255, 255, 255); flash_alpha = 150
                            audio.play(audio.snd_pound)
                            shockwaves.append([ball_x, gy, 20, 200, (255, 255, 255)])
                            
                            for obs in obstacles[:]:
                                if abs(obs.x - ball_x) < 120 and obs.type == "crate":
                                    obstacles.remove(obs)
                                    pts = 100 * combo_multiplier; score += pts
                                    stats["xp"] += 20
                                    combo_multiplier += 1; combo_timer = 120
                                    popups.append([obs.x, obs.y, f"POUND! +{pts}!", (255, 100, 50), 50])
                                    particle_pool.emit(obs.x + obs.w/2, obs.y + obs.h/2, (160, 110, 60), speed_mult=2, count=20)
                            
                        elif ball_vy > 8:
                            shake_intensity = max(shake_intensity, 5)
                            particle_pool.emit(ball_x, ball_y + ball_radius, current_biome["dirt"], count=10)
                    ball_vy = 0; on_ground = True; jumps_left = stats["max_jumps"] 
                else:
                    on_ground = False

                if on_ground: ball_angle -= scroll_speed / ball_radius
                else: ball_angle -= (scroll_speed / ball_radius) * 0.5

                ball_hitbox = pygame.Rect(ball_x - ball_radius + 4, ball_y - ball_radius + 4, (ball_radius-4)*2, (ball_radius-4)*2)
                
                for b in boost_pads[:]:
                    b.update(sub_step_speed)
                    if b.x < -100: boost_pads.remove(b)
                    elif ball_hitbox.colliderect(b.get_rect()):
                        boost_pads.remove(b)
                        scroll_speed = min(16, scroll_speed + 5)
                        shake_intensity = 6
                        flash_color = (255, 255, 0); flash_alpha = 100
                        popups.append([ball_x, ball_y - 30, "BOOST!", (255, 255, 0), 30])
                        particle_pool.emit(ball_x, ball_y, (255, 255, 0), speed_mult=2, count=15)
                        audio.play(audio.snd_boost)

                for obs in obstacles[:]:
                    obs.update(sub_step_speed)
                    if obs.x < -100: obstacles.remove(obs)
                    elif ball_hitbox.colliderect(obs.get_rect()):
                        if has_shield:
                            has_shield = False; obstacles.remove(obs); shake_intensity = 10
                            flash_color = (100, 200, 255); flash_alpha = 150
                            popups.append([obs.x, obs.y, "SHIELD BREAK!", (100, 200, 255), 40])
                            particle_pool.emit(obs.x + obs.w/2, obs.y + obs.h/2, (100, 200, 255), speed_mult=2, count=30)
                            audio.play(audio.snd_smash)
                        elif obs.type == "crate" and (scroll_speed >= stats["smash_speed"] or is_pounding):
                            obstacles.remove(obs); shake_intensity = 5
                            pts = 100 * combo_multiplier; score += pts
                            stats["xp"] += 20
                            combo_multiplier += 1; combo_timer = 120
                            popups.append([obs.x, obs.y, f"+{pts} x{combo_multiplier-1}!", (160, 110, 60), 40])
                            particle_pool.emit(obs.x + obs.w/2, obs.y + obs.h/2, (160, 110, 60), speed_mult=1.5, count=20)
                            audio.play(audio.snd_smash)
                        else:
                            state = "GAME_OVER"; shake_intensity = 25
                            flash_color = (255, 0, 0); flash_alpha = 200
                            particle_pool.emit(ball_x, ball_y, (255, 87, 51), speed_mult=1.5, count=40)
                            audio.play(audio.snd_crash)
                            if score > high_score:
                                high_score = score
                                with open(HS_FILE, "w") as f: f.write(str(high_score))

            # --- Level Up Logic ---
            if stats["xp"] >= stats["xp_needed"] and state == "PLAYING":
                stats["level"] += 1
                stats["xp"] = 0
                stats["xp_needed"] = int(stats["xp_needed"] * 1.5)
                
                upgrades = [
                    ("EXTRA JUMP!", "max_jumps", 1),
                    ("OVERDRIVE!", "base_speed", 0.5),
                    ("SMASH MASTER!", "smash_speed", -1.0),
                    ("MAGNET BOOST!", "magnet_range", 100)
                ]
                buff_name, stat_key, stat_val = random.choice(upgrades)
                stats[stat_key] += stat_val
                if stat_key == "max_jumps": jumps_left = stats["max_jumps"]
                
                popups.append([WIDTH//2, HEIGHT//2 - 100, f"LEVEL UP! {buff_name}", (255, 255, 0), 120])
                audio.play(audio.snd_levelup)
                flash_color = (255, 255, 0); flash_alpha = 150

            if biome_progress > biome_length:
                biome_progress = 0; biome_length = random.randint(1500, 3000)
                current_biome_index = (current_biome_index + 1) % len(BIOMES)
                current_biome = BIOMES[current_biome_index]
                weather_type = random.choice(["None", "None", "Rain", "Snow"])

            trail.append((ball_x, ball_y))
            if len(trail) > 12: trail.pop(0)
            if scroll_speed > 9 and random.random() < 0.4:
                speed_lines.append([WIDTH + 20, random.randint(50, HEIGHT - 150), random.randint(100, 200)])
            if on_ground and random.random() < 0.3:
                particle_pool.emit(ball_x - 10, ball_y + ball_radius, current_biome["dirt"], count=1)

            # Weather Simulation
            if weather_type == "Rain" and random.random() < 0.8:
                weather_particles.append([random.randint(-50, WIDTH), -10, 0, 12]) # x, y, vx, vy
            elif weather_type == "Snow" and random.random() < 0.5:
                weather_particles.append([random.randint(-50, WIDTH), -10, random.uniform(-1, 1), random.uniform(1, 3)])

            for wp in weather_particles[:]:
                wp[0] += wp[2] - (scroll_speed * 0.3 if weather_type == "Rain" else scroll_speed * 0.1)
                wp[1] += wp[3]
                if wp[1] > HEIGHT or wp[0] < -60: weather_particles.remove(wp)

            time_of_day = (time_of_day + 0.0002) % 1.0
            if magnet_timer > 0: magnet_timer -= 1
            if flash_alpha > 0: flash_alpha -= 10
            
            for c in clouds:
                c[0] -= scroll_speed * 0.2
                if c[0] + c[2] < 0: c[0] = WIDTH + random.randint(0, 200); c[1] = random.randint(50, 200)
            mountain_offset -= scroll_speed * 0.4

            obstacle_timer += 1
            spawn_rate = max(40, 100 - int(scroll_speed * 3))
            if obstacle_timer > random.randint(spawn_rate, spawn_rate + 60):
                obs_x = WIDTH + 50; gy = get_hill_spline_y(obs_x, hill_points)
                types = ["crate"]
                if score > 200: types.append("small_rock")
                if score > 1000: types.append("tall_rock")
                if score > 1500: types.append("spikes")
                if score > 2500: types.append("wide_rock")
                if score > 3500: types.append("flying_saw")
                if score > 4000: types.append("double_rock")
                t = random.choice(types)
                obs_y = gy - 50 if t == "tall_rock" else gy - 30
                if t == "crate": obs_y = gy - 40 
                elif t == "spikes": obs_y = gy - 20
                elif t == "flying_saw": obs_y = gy - 80
                obstacles.append(Obstacle(obs_x, obs_y, t)); obstacle_timer = 0

            coin_timer += 1
            if coin_timer > random.randint(80, 150):
                c_x = WIDTH + 50; c_by = get_hill_spline_y(c_x, hill_points)
                for i in range(3):
                    coins.append(Coin(c_x + i*30, c_by - 60 - (i * 20) - math.sin(i) * 20))
                coin_timer = 0

            powerup_timer += 1
            if powerup_timer > random.randint(800, 1500):
                powerups.append(PowerUp(WIDTH + 50, get_hill_spline_y(WIDTH + 50, hill_points) - 80, random.choice(["shield", "magnet"])))
                powerup_timer = 0

            boost_timer += 1
            if boost_timer > random.randint(400, 800):
                boost_pads.append(BoostPad(WIDTH + 50, get_hill_spline_y(WIDTH + 50, hill_points)))
                boost_timer = 0

            for c in coins[:]:
                c.update(scroll_speed)
                if c.x < -50: coins.remove(c)
                elif magnet_timer > 0:
                    dx, dy = ball_x - c.x, ball_y - c.y
                    dist = math.hypot(dx, dy)
                    if dist < stats["magnet_range"]: c.x += (dx / dist) * 8; c.y += (dy / dist) * 8

            for p in powerups[:]:
                p.update(scroll_speed)
                if p.x < -50: powerups.remove(p)

            if combo_timer > 0:
                combo_timer -= 1
                if combo_timer == 0: combo_multiplier = 1

            for c in coins[:]:
                if ball_hitbox.colliderect(c.get_rect()):
                    coins.remove(c); coins_collected += 1
                    pts = 50 * combo_multiplier; score += pts
                    stats["xp"] += 10
                    combo_multiplier += 1; combo_timer = 120
                    popups.append([c.x, c.y, f"+{pts} x{combo_multiplier-1}!", (255, 215, 0), 30])
                    particle_pool.emit(c.x, c.y, (255, 215, 0), count=8)
                    audio.play(audio.snd_coin)

            for p in powerups[:]:
                if ball_hitbox.colliderect(p.get_rect()):
                    powerups.remove(p)
                    if p.type == "shield":
                        has_shield = True
                        popups.append([p.x, p.y, "SHIELD!", (100, 200, 255), 40])
                        particle_pool.emit(p.x, p.y, (100, 200, 255), count=15)
                    else:
                        magnet_timer = 360
                        popups.append([p.x, p.y, "MAGNET!", (255, 50, 50), 40])
                        particle_pool.emit(p.x, p.y, (255, 50, 50), count=15)
                    audio.play(audio.snd_powerup)

            score += 1
            for pop in popups[:]:
                pop[1] -= 1; pop[4] -= 1
                if pop[4] <= 0: popups.remove(pop)

        # --- Drawing ---
        day_color = pygame.Color(135, 206, 235); night_color = pygame.Color(20, 20, 60); sunset_color = pygame.Color(255, 100, 100)
        sky_col = day_color; t = time_of_day
        if t < 0.25: sky_col = day_color.lerp(sunset_color, t * 4)
        elif t < 0.5: sky_col = sunset_color.lerp(night_color, (t - 0.25) * 4)
        elif t < 0.75: sky_col = night_color.lerp(sunset_color, (t - 0.5) * 4)
        else: sky_col = sunset_color.lerp(day_color, (t - 0.75) * 4)

        frame_surface.fill(sky_col)
        if time_of_day > 0.25 and time_of_day < 0.75:
            night_overlay = pygame.Surface((WIDTH, HEIGHT)); night_overlay.fill((0, 0, 30)); night_overlay.set_alpha(100)
            frame_surface.blit(night_overlay, (0,0))

        m_points = [(0, HEIGHT)]
        for i in range(int(WIDTH/100) + 3):
            m_x = i * 200 + (mountain_offset % 200); m_y = HEIGHT - 200 - (i % 2) * 50
            m_points.append((m_x, m_y)); m_points.append((m_x + 100, HEIGHT - 150 - (i % 2) * 50))
        m_points.append((WIDTH, HEIGHT))
        mountain_col = pygame.Color(current_biome["mountain"])
        if time_of_day > 0.4 and time_of_day < 0.6: mountain_col = mountain_col.lerp(night_color, 0.6)
        pygame.draw.polygon(frame_surface, mountain_col, m_points)

        cloud_col = (255, 255, 255) if time_of_day < 0.5 else (150, 150, 150)
        for c in clouds:
            pygame.draw.ellipse(frame_surface, cloud_col, (c[0], c[1], c[2], c[2]//2))
            pygame.draw.ellipse(frame_surface, cloud_col, (c[0]+20, c[1]-15, c[2]*0.8, c[2]//2))

        for sl in speed_lines[:]:
            sl[0] -= scroll_speed * 2.5
            pygame.draw.line(frame_surface, (255, 255, 255), (sl[0], sl[1]), (sl[0] + sl[2], sl[1]), 2)
            if sl[0] + sl[2] < 0: speed_lines.remove(sl)

        grass_col = pygame.Color(current_biome["grass"]); dirt_col = pygame.Color(current_biome["dirt"])
        if time_of_day > 0.4 and time_of_day < 0.6:
            grass_col = grass_col.lerp(night_color, 0.5); dirt_col = dirt_col.lerp(night_color, 0.5)

        poly_points = [(0, HEIGHT)]
        for x in range(0, WIDTH + 10, 5): poly_points.append((x, get_hill_spline_y(x, hill_points)))
        poly_points.append((WIDTH, HEIGHT))
        pygame.draw.polygon(frame_surface, grass_col, poly_points)
        
        dirt_points = [(0, HEIGHT)] + [(p[0], p[1] + 30) for p in poly_points[1:-1]] + [(WIDTH, HEIGHT)]
        pygame.draw.polygon(frame_surface, dirt_col, dirt_points)
        pygame.draw.lines(frame_surface, current_biome["line"], False, poly_points[1:-1], 5)

        for d in terrain_decor:
            dy = get_hill_spline_y(d[0], hill_points)
            if d[2] == "tuft":
                pygame.draw.line(frame_surface, current_biome["decor"], (d[0], dy), (d[0]-3, dy-6), 2)
                pygame.draw.line(frame_surface, current_biome["decor"], (d[0], dy), (d[0], dy-8), 2)
                pygame.draw.line(frame_surface, current_biome["decor"], (d[0], dy), (d[0]+3, dy-6), 2)
            else:
                pygame.draw.circle(frame_surface, current_biome["decor"], (int(d[0]), int(dy+5)), 3)

        for b in boost_pads: b.draw(frame_surface)
        for obs in obstacles:
            obs.draw(frame_surface, get_hill_spline_y(obs.x, hill_points))
        for c in coins: c.draw(frame_surface)
        for p in powerups: p.draw(frame_surface)

        particle_pool.update_and_draw(frame_surface)

        # Draw Shockwaves
        for sw in shockwaves[:]:
            sw[2] += (sw[3] - sw[2]) * 0.2
            if sw[2] > sw[3] - 5: shockwaves.remove(sw)
            else:
                pygame.draw.circle(frame_surface, sw[4], (int(sw[0]), int(sw[1])), int(sw[2]), 4)

        # Draw Weather
        for wp in weather_particles:
            if weather_type == "Rain":
                pygame.draw.line(frame_surface, (100, 150, 200), (wp[0], wp[1]), (wp[0]-3, wp[1]+8), 2)
            else:
                pygame.draw.circle(frame_surface, (255, 255, 255), (int(wp[0]), int(wp[1])), 2)

        if state == "PLAYING" or state == "GAME_OVER":
            for i, t in enumerate(trail):
                alpha = (i / len(trail))
                t_radius = int(ball_radius * alpha * 0.7)
                if t_radius > 0:
                    pygame.draw.circle(frame_surface, (200, 50, 30), (int(t[0]), int(t[1])), t_radius)

        if state != "MENU":
            if has_shield: pygame.draw.circle(frame_surface, (100, 200, 255), (int(ball_x), int(ball_y)), ball_radius + 8, 3)
            if magnet_timer > 0: pygame.draw.circle(frame_surface, (255, 50, 50), (int(ball_x), int(ball_y)), ball_radius + 12, 2)
            if is_pounding: 
                pygame.draw.circle(frame_surface, (255, 255, 255), (int(ball_x), int(ball_y)), ball_radius + (15 - ball_radius), 4)
                
            if on_ground: vis_angle = math.degrees(get_hill_angle(ball_x, hill_points)) + math.degrees(ball_angle)
            else: vis_angle = math.degrees(ball_angle)
                
            scale_y = 1.0 - max(-0.3, min(0.3, ball_vy * 0.05))
            scale_x = 1.0 + (1.0 - scale_y)
            
            scaled_surf = pygame.transform.scale(ball_surf, (int(ball_surf.get_width() * scale_x), int(ball_surf.get_height() * scale_y)))
            rotated_surf = pygame.transform.rotate(scaled_surf, vis_angle)
            rect = rotated_surf.get_rect(center=(int(ball_x), int(ball_y)))
            frame_surface.blit(rotated_surf, rect)

        for pop in popups:
            alpha = min(255, pop[4] * 6)
            txt_surf = small_font.render(pop[2], True, pop[3])
            txt_surf.set_alpha(alpha)
            frame_surface.blit(txt_surf, (pop[0] - txt_surf.get_width()//2, pop[1]))

        # Apply Vignette & Flash
        frame_surface.blit(vignette, (0,0))
        if flash_alpha > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT))
            flash_surf.fill(flash_color)
            flash_surf.set_alpha(flash_alpha)
            frame_surface.blit(flash_surf, (0,0), special_flags=pygame.BLEND_RGB_ADD)

        screen.fill((0,0,0))
        screen.blit(frame_surface, (shake_x, shake_y))

        # --- UI ---
        if state == "MENU":
            draw_text("ROLLING BALL", large_font, (255, 255, 255), WIDTH//2, HEIGHT//2 - 80, center=True)
            draw_text("Press ENTER to Start", font, (255, 255, 255), WIDTH//2, HEIGHT//2 + 20, center=True)
            draw_text(f"High Score: {high_score}", small_font, (255, 215, 0), WIDTH//2, HEIGHT//2 + 70, center=True)
            draw_text("Roguelite Upgrades | Weather | Ground Pounds", tiny_font, (200, 200, 200), WIDTH//2, HEIGHT - 50, center=True)

        elif state == "PLAYING":
            draw_text(f"Score: {score}", font, (255, 255, 255), 20, 20)
            draw_text(f"Coins: {coins_collected}", small_font, (255, 215, 0), 20, 60)
            draw_text(f"Biome: {current_biome['name']} ({weather_type})", small_font, (255, 255, 255), 20, 90)
            
            speed_col = (255, 255, 255) if scroll_speed < stats["smash_speed"] else (160, 110, 60)
            draw_text(f"Speed: {int(scroll_speed * 10)}km/h", tiny_font, speed_col, 20, 120)
            
            if combo_multiplier > 1:
                combo_col = (255, 255, 0) if combo_timer > 40 else (255, 100, 100)
                draw_text(f"COMBO x{combo_multiplier} ({int(combo_timer/60+1)})", small_font, combo_col, 20, 150)
                
            if has_shield: draw_text("SHIELD", tiny_font, (100, 200, 255), WIDTH - 150, 20)
            if magnet_timer > 0: draw_text("MAGNET", tiny_font, (255, 50, 50), WIDTH - 150, 40)
            
            # Draw XP Bar
            xp_bar_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT - 30, 200, 15)
            pygame.draw.rect(screen, (50, 50, 50), xp_bar_rect, border_radius=5)
            xp_fill = int((stats["xp"] / stats["xp_needed"]) * 198)
            pygame.draw.rect(screen, (100, 255, 100), (WIDTH//2 - 99, HEIGHT - 29, xp_fill, 13), border_radius=5)
            draw_text(f"Lvl {stats['level']}", tiny_font, (255, 255, 255), WIDTH//2, HEIGHT - 38, center=True)

        elif state == "GAME_OVER":
            draw_text("GAME OVER", large_font, (255, 50, 50), WIDTH//2, HEIGHT//2 - 60, center=True)
            draw_text(f"Score: {score}", font, (255, 255, 255), WIDTH//2, HEIGHT//2 + 10, center=True)
            if score == high_score and score > 0:
                 draw_text("NEW HIGH SCORE!", small_font, (255, 215, 0), WIDTH//2, HEIGHT//2 + 45, center=True)
            else:
                 draw_text(f"High Score: {high_score}", font, (255, 215, 0), WIDTH//2, HEIGHT//2 + 50, center=True)
            draw_text("Press ENTER to Restart", small_font, (200, 200, 200), WIDTH//2, HEIGHT//2 + 110, center=True)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()