"""
CSE423 Project: Space Shooter 3D - Professional Edition
A complete 3D space shooter game with polished features and visuals
Section: 10
"""

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

WIN_WIDTH = 1400
WIN_HEIGHT = 900
WORLD_SIZE = 300  # Much bigger play area
BOUNDARY_MIN = -WORLD_SIZE
BOUNDARY_MAX = WORLD_SIZE

# Game states
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2

# Difficulty settings - MUCH SLOWER speeds
DIFFICULTIES = {
    'easy': {'enemy_speed': 0.015, 'spawn_rate': 200, 'meteor_speed': 0.012},
    'medium': {'enemy_speed': 0.025, 'spawn_rate': 150, 'meteor_speed': 0.02},
    'hard': {'enemy_speed': 0.04, 'spawn_rate': 100, 'meteor_speed': 0.03}
}

# ============================================================================
# GAME STATE
# ============================================================================

class GameState:
    def __init__(self):
        self.state = STATE_MENU
        self.difficulty = 'easy'
        self.health = 100
        self.max_health = 100
        self.score = 0
        self.level = 1
        self.kills = 0
        self.ammo_missiles = 0
        self.weapon_unlocked = False
        self.current_weapon = 'primary'
        self.gun_type = 1  # 1 = normal, 2 = heavy
        self.bullet_speed_bonus = 0  # Increases every 10 kills
        self.fire_cooldown = 0
        self.missile_cooldown = 0
        self.camera_mode = 'third'
        self.show_rear_mirror = False
        self.cheat_mode = False
        self.frame_count = 0
        self.spawn_timer = 0
        self.meteor_timer = 0
        self.powerup_timer = 0
        self.paused = False
        self.wave_number = 1
        self.enemies_per_wave = 5
        self.wave_spawned = 0
        self.in_black_hole_death = False
        self.death_animation_timer = 0
        self.boss_killed_at = set()  # Track which kill counts spawned bosses
        self.invisibility_timer = 0  # Invisibility powerup timer (frames)
        self.last_enemy_increase = 0  # Track when we last increased enemy count

game = GameState()

# ============================================================================
# PLAYER SPACESHIP
# ============================================================================

class Player:
    def __init__(self):
        self.x = 0.0
        self.y = 10.0
        self.z = 0.0
        self.rotation_y = 0.0
        self.rotation_z = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.acceleration = 0.4  # Faster acceleration
        self.max_speed = 0.9  # Faster max speed
        self.friction = 0.94
        
    def move_forward(self):
        angle = math.radians(self.rotation_y)
        self.vx += math.sin(angle) * self.acceleration
        self.vz += math.cos(angle) * self.acceleration
        
    def move_backward(self):
        angle = math.radians(self.rotation_y)
        self.vx -= math.sin(angle) * self.acceleration * 0.6
        self.vz -= math.cos(angle) * self.acceleration * 0.6
        
    def move_left(self):
        # A key - move LEFT (rotation_y + 90 for left side)
        angle = math.radians(self.rotation_y + 90)
        self.vx += math.sin(angle) * self.acceleration * 0.8
        self.vz += math.cos(angle) * self.acceleration * 0.8
        self.rotation_z = min(20, self.rotation_z + 2.5)
        
    def move_right(self):
        # D key - move RIGHT (rotation_y - 90 for right side)
        angle = math.radians(self.rotation_y - 90)
        self.vx += math.sin(angle) * self.acceleration * 0.8
        self.vz += math.cos(angle) * self.acceleration * 0.8
        self.rotation_z = max(-20, self.rotation_z - 2.5)
        
    def move_up(self):
        self.vy += self.acceleration * 0.6
        
    def move_down(self):
        self.vy -= self.acceleration * 0.6
        
    def rotate_left(self):
        self.rotation_y = (self.rotation_y + 3.5) % 360
        
    def rotate_right(self):
        self.rotation_y = (self.rotation_y - 3.5) % 360
        
    def update(self):
        # Limit speed
        speed = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed
            self.vz = (self.vz / speed) * self.max_speed
            
        # Apply velocity
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz
        
        # Apply friction
        self.vx *= self.friction
        self.vy *= self.friction
        self.vz *= self.friction
        
        # Reset roll
        if abs(self.rotation_z) > 0.5:
            self.rotation_z *= 0.88
        else:
            self.rotation_z = 0
            
        # Boundaries - much bigger area for 3D movement
        self.x = max(BOUNDARY_MIN + 20, min(BOUNDARY_MAX - 20, self.x))
        self.y = max(2, min(120, self.y))  # Can fly much higher
        self.z = max(BOUNDARY_MIN + 20, min(BOUNDARY_MAX - 20, self.z))

player = Player()

# ============================================================================
# PROJECTILES
# ============================================================================

class Bullet:
    def __init__(self, x, y, z, rotation, gun_type=1):
        self.x = x
        self.y = y
        self.z = z
        self.rotation = rotation
        self.gun_type = gun_type
        # Base speed MUCH slower + bonus from kills
        base_speed = 0.5 if gun_type == 1 else 0.35  # Heavy gun slower
        self.speed = base_speed + game.bullet_speed_bonus
        self.lifetime = 250  # Longer lifetime for slower bullets
        self.active = True
        self.damage = 1 if gun_type == 1 else 2  # Heavy gun does more damage
        
    def update(self):
        angle = math.radians(self.rotation)
        self.x += math.sin(angle) * self.speed
        self.z += math.cos(angle) * self.speed
        self.lifetime -= 1
        if self.lifetime <= 0 or abs(self.x) > WORLD_SIZE or abs(self.z) > WORLD_SIZE:
            self.active = False

class Missile:
    def __init__(self, x, y, z, rotation, target=None):
        self.x = x
        self.y = y
        self.z = z
        self.rotation = rotation
        self.speed = 0.7
        self.lifetime = 180
        self.active = True
        self.target = target
        self.trail = []
        
    def update(self):
        # Homing
        if self.target and self.target.active:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            dz = self.target.z - self.z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist > 0.1:
                target_angle = math.degrees(math.atan2(dx, dz))
                angle_diff = (target_angle - self.rotation + 180) % 360 - 180
                self.rotation += angle_diff * 0.08
                self.y += (dy / dist) * self.speed * 0.4
                
        # Move
        angle = math.radians(self.rotation)
        self.x += math.sin(angle) * self.speed
        self.z += math.cos(angle) * self.speed
        
        # Trail
        self.trail.append((self.x, self.y, self.z))
        if len(self.trail) > 15:
            self.trail.pop(0)
            
        self.lifetime -= 1
        if self.lifetime <= 0 or abs(self.x) > WORLD_SIZE or \
           abs(self.z) > WORLD_SIZE:
            self.active = False


class EnemyBullet:
    def __init__(self, x, y, z, target_x, target_y, target_z, boss_tier=0):
        self.x = x
        self.y = y
        self.z = z
        self.boss_tier = boss_tier  # Track which boss fired this
        # Calculate FIXED direction at spawn - bullet goes straight, doesn't chase
        dx = target_x - x
        dy = target_y - y
        dz = target_z - z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        speed = 0.08  # Bullet speed
        if dist > 0:
            # Store FIXED direction - won't change
            self.dir_x = dx / dist
            self.dir_y = dy / dist
            self.dir_z = dz / dist
        else:
            self.dir_x = 0
            self.dir_y = 0
            self.dir_z = 1
        self.speed = speed
        self.lifetime = 500  # Longer lifetime for fixed direction bullets
        self.active = True
        
    def update(self):
        # Move in FIXED direction (like meteor/blackhole - doesn't chase)
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed
        self.z += self.dir_z * self.speed
        self.lifetime -= 1
        if self.lifetime <= 0 or abs(self.x) > WORLD_SIZE or \
           abs(self.z) > WORLD_SIZE:
            self.active = False


bullets = []
missiles = []
enemy_bullets = []


# ============================================================================
# ENEMIES
# ============================================================================

class Enemy:
    def __init__(self, x, y, z, enemy_type='basic', boss_tier=0):
        self.x = x
        self.y = y
        self.z = z
        self.type = enemy_type
        self.boss_tier = boss_tier
        self.rotation = 0
        self.active = True
        if enemy_type == 'boss':
            # Boss health: 15 for tier 1, 20 for tier 2, 25 for tier 3, etc.
            self.health = 15 + (boss_tier - 1) * 5
        else:
            self.health = 3
        self.max_health = self.health
        self.speed = DIFFICULTIES[game.difficulty]['enemy_speed'] * (1 if enemy_type == 'basic' else 0.6)
        self.size = 1.2 if enemy_type == 'basic' else 3.0  # Boss bigger
        self.oscillate = 0
        self.fire_cooldown = 0
        self.fire_rate = 200 if enemy_type == 'basic' else 150  # Much slower firing
        
    def update(self):
        dx = player.x - self.x
        dy = player.y - self.y
        dz = player.z - self.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        # ALWAYS chase player - no distance limit, try to collide!
        if dist > 2.0:  # Only stop when very close (collision range)
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed * 0.6  # Better vertical tracking
            self.z += (dz / dist) * self.speed
            
            self.oscillate += 0.08
            self.y += math.sin(self.oscillate) * 0.02
            
        self.rotation = math.degrees(math.atan2(dx, dz))
        
        # Enemy firing - only when in effective range (60 units where bullet can hit)
        self.fire_cooldown -= 1
        if self.fire_cooldown <= 0 and dist < 60:  # Fire ONLY when in range to hit
            enemy_bullets.append(EnemyBullet(self.x, self.y, self.z, 
                                             player.x, player.y, player.z, 
                                             self.boss_tier if self.type == 'boss' else 0))
            self.fire_cooldown = self.fire_rate
        
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.active = False
            return True
        return False

enemies = []

# ============================================================================
# OBSTACLES & POWER-UPS
# ============================================================================

class Meteor:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.size = random.uniform(1.0, 1.8)
        self.active = True
        # Very slow meteor speed based on difficulty
        self.speed = DIFFICULTIES[game.difficulty]['meteor_speed']
        
        # Calculate FIXED direction toward player's CURRENT position
        # This direction will NOT change even if player moves
        dx = player.x - x
        dy = player.y - y
        dz = player.z - z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist > 0:
            self.dir_x = dx / dist
            self.dir_y = dy / dist
            self.dir_z = dz / dist
        else:
            self.dir_x = 0
            self.dir_y = 0
            self.dir_z = 1
        
        self.rx = random.uniform(0, 360)
        self.ry = random.uniform(0, 360)
        self.rz = random.uniform(0, 360)

    def update(self):
        # Move in FIXED direction (doesn't track player) - full 3D movement
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed  # Full Y movement
        self.z += self.dir_z * self.speed
        
        self.rx += 1.5
        self.ry += 1.2
        self.rz += 1.0
        
        # Deactivate if too far
        if abs(self.x) > WORLD_SIZE * 2 or abs(self.z) > WORLD_SIZE * 2 or self.y < -30 or self.y > 160:
            self.active = False


class BlackHole:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        
        # Calculate FIXED direction toward player's position at spawn
        dx = player.x - x
        dy = player.y - y
        dz = player.z - z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.speed = 0.025  # Slightly faster black hole
        if dist > 0:
            self.dir_x = dx / dist
            self.dir_y = dy / dist
            self.dir_z = dz / dist
        else:
            self.dir_x = 0
            self.dir_y = 0
            self.dir_z = 1

        # SMALLER black hole
        self.pull_radius = 6.0  # Smaller pull radius
        self.kill_radius = 1.0  # Smaller kill radius
        self.rotation = 0
        self.active = True

    def update(self):
        self.rotation += 2.0
        
        # Move in FIXED direction (doesn't track player) - full 3D
        self.x += self.dir_x * self.speed
        self.y += self.dir_y * self.speed  # Full Y movement
        self.z += self.dir_z * self.speed

        dx = self.x - player.x
        dy = self.y - player.y
        dz = self.z - player.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < self.pull_radius and dist > self.kill_radius:
            pull = 0.08 * (1 - dist / self.pull_radius)
            player.vx += (dx / dist) * pull
            player.vy += (dy / dist) * pull
            player.vz += (dz / dist) * pull

        elif dist < self.kill_radius:
            game.in_black_hole_death = True
            game.death_animation_timer = 120

        # Deactivate if too far - bigger bounds for full 3D
        if abs(self.x) > WORLD_SIZE * 2 or abs(self.z) > WORLD_SIZE * 2 or self.y < -30 or self.y > 160:
            self.active = False


class PowerUp:
    def __init__(self, x, y, z, ptype):
        self.x = x
        self.y = y
        self.z = z
        self.type = ptype
        self.rotation = 0
        self.float_offset = 0
        self.active = True
        
    def update(self):
        self.rotation += 4
        self.float_offset += 0.12
        self.y += math.sin(self.float_offset) * 0.025
        
        dx = self.x - player.x
        dy = self.y - player.y
        dz = self.z - player.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if dist < 2.5:
            self.apply_effect()
            self.active = False
            
        if self.z > player.z + 35:
            self.active = False
            
    def apply_effect(self):
        if self.type == 'health':
            game.health = min(game.max_health, game.health + 30)
            print("💚 Health restored +30!")
        elif self.type == 'ammo':
            game.ammo_missiles += 5
            print("🚀 Missiles +5!")
        elif self.type == 'speed':
            player.max_speed = min(1.2, player.max_speed + 0.05)
            print("⚡ Speed increased!")
        elif self.type == 'invisibility':
            # 5 seconds at ~60 FPS = 300 frames
            game.invisibility_timer = 300
            print("👻 INVISIBILITY ACTIVATED! 5 seconds - Enemies can't see you!")

meteors = []
black_holes = []
powerups = []
stars = []

# ============================================================================
# EFFECTS
# ============================================================================

class Explosion:
    def __init__(self, x, y, z, size=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.particles = []
        for _ in range(int(25 * size)):
            self.particles.append({
                'x': x, 'y': y, 'z': z,
                'vx': random.uniform(-0.35, 0.35),
                'vy': random.uniform(-0.35, 0.35),
                'vz': random.uniform(-0.35, 0.35),
                'life': int(35 * size),
                'size': random.uniform(0.1, 0.3) * size
            })
        self.active = True
        
    def update(self):
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['z'] += p['vz']
            p['vx'] *= 0.96
            p['vy'] *= 0.96
            p['vz'] *= 0.96
            p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]
        if not self.particles:
            self.active = False

explosions = []

# ============================================================================
# DRAWING FUNCTIONS
# ============================================================================

def setup_lighting():
    """Setup professional lighting"""
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    # Key light
    glLightfv(GL_LIGHT0, GL_POSITION, [20, 30, 20, 1])
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.4, 1])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 1.0, 1])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1, 1, 1, 1])
    
    # Fill light
    glLightfv(GL_LIGHT1, GL_POSITION, [-15, 20, -15, 1])
    glLightfv(GL_LIGHT1, GL_AMBIENT, [0.2, 0.2, 0.25, 1])
    glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.4, 0.4, 0.6, 1])

def draw_spaceship():
    """Draw player spaceship with enhanced details"""
    glPushMatrix()
    glTranslatef(player.x, player.y, player.z)
    glRotatef(player.rotation_y, 0, 1, 0)
    glRotatef(player.rotation_z, 0, 0, 1)
    
    # Main fuselage
    glColor3f(0.75, 0.75, 0.85)
    glPushMatrix()
    glScalef(0.9, 0.45, 2.2)
    glutSolidCube(1)
    glPopMatrix()
    
    # Cockpit
    glColor3f(0.2, 0.4, 0.9)
    glPushMatrix()
    glTranslatef(0, 0.35, -0.6)
    glScalef(0.55, 0.35, 0.9)
    glutSolidCube(1)
    glPopMatrix()
    
    # Nose cone
    glColor3f(0.65, 0.65, 0.75)
    glPushMatrix()
    glTranslatef(0, 0, -1.3)
    glRotatef(-90, 1, 0, 0)
    glutSolidCone(0.3, 0.5, 8, 8)
    glPopMatrix()
    
    # Wings
    glColor3f(0.7, 0.7, 0.8)
    for side in [-1.3, 1.3]:
        glPushMatrix()
        glTranslatef(side, 0, 0.25)
        glScalef(1.6, 0.12, 1.1)
        glutSolidCube(1)
        glPopMatrix()
        
        # Wing tips
        glColor3f(1.0, 0.2, 0.2)
        glPushMatrix()
        glTranslatef(side * 1.4, 0, 0.25)
        glutSolidSphere(0.15, 8, 8)
        glPopMatrix()
    
    # Engines
    glColor3f(0.35, 0.35, 0.45)
    for ex in [-0.55, 0.55]:
        glPushMatrix()
        glTranslatef(ex, 0, 1.3)
        glRotatef(-90, 1, 0, 0)
        glutSolidCone(0.2, 0.5, 8, 8)
        glPopMatrix()
        
        # Engine glow
        glDisable(GL_LIGHTING)
        glColor3f(0.3, 0.6, 1.0)
        glPushMatrix()
        glTranslatef(ex, 0, 1.5)
        glutSolidSphere(0.15, 8, 8)
        glPopMatrix()
        glEnable(GL_LIGHTING)
    
    glPopMatrix()

def draw_enemy(enemy):
    """Draw enemy spaceship"""
    if not enemy.active:
        return
        
    glPushMatrix()
    glTranslatef(enemy.x, enemy.y, enemy.z)
    glRotatef(enemy.rotation, 0, 1, 0)
    glScalef(enemy.size, enemy.size, enemy.size)
    
    # Color based on type
    if enemy.type == 'boss':
        glColor3f(0.85, 0.1, 0.85)
    else:
        glColor3f(0.95, 0.2, 0.2)
    
    # Body
    glPushMatrix()
    glScalef(0.7, 0.35, 1.1)
    glutSolidCube(1)
    glPopMatrix()
    
    # Cockpit
    glColor3f(1.0, 1.0, 0.2)
    glPushMatrix()
    glTranslatef(0, 0.25, -0.35)
    glutSolidSphere(0.25, 8, 8)
    glPopMatrix()
    
    # Wings
    glColor3f(0.75, 0.15, 0.15) if enemy.type == 'basic' else glColor3f(0.7, 0.1, 0.7)
    for wx in [-0.9, 0.9]:
        glPushMatrix()
        glTranslatef(wx, 0, 0)
        glScalef(0.9, 0.06, 0.7)
        glutSolidCube(1)
        glPopMatrix()
    
    glPopMatrix()
    
    # Health bar - for boss show bullet count
    if enemy.type == 'boss':
        draw_boss_health_3d(enemy.x, enemy.y + enemy.size + 0.7, enemy.z,
                           enemy.health, enemy.max_health, 1.5)
    else:
        draw_health_bar_3d(enemy.x, enemy.y + enemy.size + 0.7, enemy.z, 
                           enemy.health / enemy.max_health, 1.2)

def draw_health_bar_3d(x, y, z, ratio, width):
    """Draw 3D health bar above enemies"""
    glDisable(GL_LIGHTING)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-player.rotation_y, 0, 1, 0)
    
    # Background
    glColor3f(0.9, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex3f(-width/2, 0, 0)
    glVertex3f(width/2, 0, 0)
    glVertex3f(width/2, 0.15, 0)
    glVertex3f(-width/2, 0.15, 0)
    glEnd()
    
    # Foreground
    glColor3f(0.0, 1.0, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-width/2, 0, 0)
    glVertex3f(-width/2 + width * ratio, 0, 0)
    glVertex3f(-width/2 + width * ratio, 0.15, 0)
    glVertex3f(-width/2, 0.15, 0)
    glEnd()
    
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_boss_health_3d(x, y, z, health, max_health, width):
    """Draw boss health bar with bullet count (health = bullets needed to kill)"""
    glDisable(GL_LIGHTING)
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-player.rotation_y, 0, 1, 0)
    
    ratio = health / max_health
    
    # Background - dark purple for boss
    glColor3f(0.4, 0.0, 0.4)
    glBegin(GL_QUADS)
    glVertex3f(-width/2, 0, 0)
    glVertex3f(width/2, 0, 0)
    glVertex3f(width/2, 0.2, 0)
    glVertex3f(-width/2, 0.2, 0)
    glEnd()
    
    # Foreground - bright magenta
    glColor3f(1.0, 0.2, 1.0)
    glBegin(GL_QUADS)
    glVertex3f(-width/2, 0, 0)
    glVertex3f(-width/2 + width * ratio, 0, 0)
    glVertex3f(-width/2 + width * ratio, 0.2, 0)
    glVertex3f(-width/2, 0.2, 0)
    glEnd()
    
    # Draw text showing bullets remaining
    glColor3f(1.0, 1.0, 1.0)
    glRasterPos3f(-0.3, 0.35, 0)
    hp_text = f"{int(health)} HP"
    for char in hp_text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
    
    glPopMatrix()
    glEnable(GL_LIGHTING)
    
    # Foreground
    glColor3f(0.0, 1.0, 0.2)
    glBegin(GL_QUADS)
    glVertex3f(-width/2, 0, 0)
    glVertex3f(-width/2 + width * ratio, 0, 0)
    glVertex3f(-width/2 + width * ratio, 0.15, 0)
    glVertex3f(-width/2, 0.15, 0)
    glEnd()
    
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_bullet(bullet):
    """Draw bullet projectile - different colors/sizes for gun types"""
    if not bullet.active:
        return
    glDisable(GL_LIGHTING)
    
    if bullet.gun_type == 1:
        # Normal gun - yellow, small
        glColor3f(1.0, 1.0, 0.3)
        glPushMatrix()
        glTranslatef(bullet.x, bullet.y, bullet.z)
        glRotatef(bullet.rotation, 0, 1, 0)
        glScalef(0.12, 0.12, 0.5)
        glutSolidCube(1)
        glPopMatrix()
    else:
        # Heavy gun - cyan/blue, bigger
        glColor3f(0.2, 0.8, 1.0)
        glPushMatrix()
        glTranslatef(bullet.x, bullet.y, bullet.z)
        glRotatef(bullet.rotation, 0, 1, 0)
        glScalef(0.2, 0.2, 0.7)
        glutSolidCube(1)
        glPopMatrix()
        # Add glow effect
        glColor4f(0.3, 0.9, 1.0, 0.4)
        glPushMatrix()
        glTranslatef(bullet.x, bullet.y, bullet.z)
        glutSolidSphere(0.25, 8, 8)
        glPopMatrix()
    
    glEnable(GL_LIGHTING)

def draw_enemy_bullet(bullet):
    """Draw enemy bullet - PURE RED but smaller (like player bullet)"""
    if not bullet.active:
        return
    glDisable(GL_LIGHTING)
    
    # Outer glow - dark red (smaller)
    glColor4f(0.8, 0.0, 0.0, 0.5)
    glPushMatrix()
    glTranslatef(bullet.x, bullet.y, bullet.z)
    glutSolidSphere(0.2, 8, 8)  # Smaller - like player bullet
    glPopMatrix()
    
    # Pure red core - visible but small
    glColor3f(1.0, 0.0, 0.0)
    glPushMatrix()
    glTranslatef(bullet.x, bullet.y, bullet.z)
    glutSolidSphere(0.12, 8, 8)  # Smaller core
    glPopMatrix()
    
    glEnable(GL_LIGHTING)

def draw_missile(missile):
    """Draw missile with trail"""
    if not missile.active:
        return
        
    glDisable(GL_LIGHTING)
    
    # Trail
    if len(missile.trail) > 1:
        glLineWidth(3)
        glBegin(GL_LINE_STRIP)
        for i, pos in enumerate(missile.trail):
            alpha = i / len(missile.trail)
            glColor3f(1.0, 0.5 * alpha, 0.1)
            glVertex3f(*pos)
        glEnd()
    
    glEnable(GL_LIGHTING)
    
    # Missile body
    glColor3f(1.0, 0.35, 0.1)
    glPushMatrix()
    glTranslatef(missile.x, missile.y, missile.z)
    glRotatef(missile.rotation, 0, 1, 0)
    
    glPushMatrix()
    glScalef(0.18, 0.18, 0.7)
    glutSolidCube(1)
    glPopMatrix()
    
    # Nose
    glPushMatrix()
    glTranslatef(0, 0, -0.5)
    glRotatef(-90, 1, 0, 0)
    glutSolidCone(0.12, 0.25, 8, 8)
    glPopMatrix()
    
    glPopMatrix()


def draw_meteor(meteor):
    """Draw rotating meteor"""
    if not meteor.active:
        return
    glColor3f(0.55, 0.45, 0.35)
    glPushMatrix()
    glTranslatef(meteor.x, meteor.y, meteor.z)
    glRotatef(meteor.rx, 1, 0, 0)
    glRotatef(meteor.ry, 0, 1, 0)
    glRotatef(meteor.rz, 0, 0, 1)
    glutSolidSphere(meteor.size, 10, 10)
    glPopMatrix()

def draw_black_hole(bh):
    """Draw black hole with gravitational visualization - SMALLER"""
    if not bh.active:
        return
        
    glDisable(GL_LIGHTING)
    
    # Pull radius visualization (smaller)
    glColor3f(0.5, 0.0, 0.5)
    glPushMatrix()
    glTranslatef(bh.x, bh.y, bh.z)
    glutWireSphere(bh.pull_radius, 16, 16)
    glPopMatrix()
    
    glEnable(GL_LIGHTING)
    
    # Core - SMALLER
    glColor3f(0.0, 0.0, 0.0)
    glPushMatrix()
    glTranslatef(bh.x, bh.y, bh.z)
    glutSolidSphere(0.8, 16, 16)  # Much smaller core
    glPopMatrix()
    
    # Accretion disk - smaller
    glDisable(GL_LIGHTING)
    glColor3f(0.9, 0.35, 0.1)
    glPushMatrix()
    glTranslatef(bh.x, bh.y, bh.z)
    glRotatef(bh.rotation, 0, 1, 0)
    for angle in range(0, 360, 30):  # Fewer pieces
        glPushMatrix()
        glRotatef(angle, 0, 1, 0)
        glTranslatef(1.5, 0, 0)  # Closer to core
        glutSolidCube(0.3)  # Smaller cubes
        glPopMatrix()
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_powerup(pu):
    """Draw rotating power-up"""
    if not pu.active:
        return
        
    colors = {
        'health': (0.1, 1.0, 0.1),      # Green
        'ammo': (1.0, 1.0, 0.2),         # Yellow
        'speed': (0.2, 0.6, 1.0),        # Blue
        'invisibility': (0.8, 0.2, 1.0)  # Purple
    }
    
    glDisable(GL_LIGHTING)
    glColor3f(*colors.get(pu.type, (1, 1, 1)))
    glPushMatrix()
    glTranslatef(pu.x, pu.y, pu.z)
    glRotatef(pu.rotation, 0, 1, 0)
    glRotatef(pu.rotation, 1, 0, 0)
    
    # Invisibility powerup has special shape (star-like)
    if pu.type == 'invisibility':
        glutSolidSphere(0.6, 12, 12)
        # Add glow effect
        glColor4f(0.9, 0.3, 1.0, 0.5)
        glutWireSphere(0.9, 8, 8)
    else:
        glutSolidCube(0.9)
    
    glPopMatrix()
    glEnable(GL_LIGHTING)

def draw_explosion(exp):
    """Draw particle explosion"""
    if not exp.active:
        return
    glDisable(GL_LIGHTING)
    for p in exp.particles:
        alpha = p['life'] / 35.0
        glColor3f(1.0, alpha * 0.7, 0.0)
        glPointSize(p['size'] * 10)
        glBegin(GL_POINTS)
        glVertex3f(p['x'], p['y'], p['z'])
        glEnd()
    glEnable(GL_LIGHTING)

def draw_starfield():
    """Draw background stars - realistic space"""
    glDisable(GL_LIGHTING)
    
    # Draw different sized stars
    for i, star in enumerate(stars):
        # Vary star brightness
        brightness = 0.5 + (i % 5) * 0.1
        glColor3f(brightness, brightness, brightness + 0.1)
        
        # Larger stars for closer ones
        if i % 10 == 0:
            glPointSize(3.5)
        elif i % 5 == 0:
            glPointSize(2.5)
        else:
            glPointSize(1.5)
        
        glBegin(GL_POINTS)
        glVertex3f(*star)
        glEnd()
    
    glEnable(GL_LIGHTING)

def draw_skybox():
    """Draw space environment - realistic deep space"""
    glDisable(GL_LIGHTING)
    size = WORLD_SIZE * 3
    
    # Dark space bottom with slight purple tint
    glBegin(GL_QUADS)
    glColor3f(0.02, 0.01, 0.05)
    glVertex3f(-size, -15, -size)
    glVertex3f(size, -15, -size)
    glVertex3f(size, -15, size)
    glVertex3f(-size, -15, size)
    glEnd()
    
    # Space top - darker
    glBegin(GL_QUADS)
    glColor3f(0.0, 0.0, 0.02)
    glVertex3f(-size, 60, -size)
    glVertex3f(size, 60, -size)
    glVertex3f(size, 60, size)
    glVertex3f(-size, 60, size)
    glEnd()
    
    # Distant nebula effect (subtle colored patches)
    glColor4f(0.1, 0.05, 0.2, 0.3)
    glPushMatrix()
    glTranslatef(-80, 40, -200)
    glutSolidSphere(30, 16, 16)
    glPopMatrix()
    
    glColor4f(0.05, 0.1, 0.2, 0.3)
    glPushMatrix()
    glTranslatef(100, 35, -180)
    glutSolidSphere(25, 16, 16)
    glPopMatrix()
    
    glEnable(GL_LIGHTING)

def draw_grid():
    """Draw reference grid - bigger grid for larger world"""
    glDisable(GL_LIGHTING)
    glColor3f(0.08, 0.08, 0.15)
    glLineWidth(1)
    glBegin(GL_LINES)
    # Bigger grid for larger world
    for i in range(-250, 251, 15):
        glVertex3f(i, 0, -250)
        glVertex3f(i, 0, 250)
        glVertex3f(-250, 0, i)
        glVertex3f(250, 0, i)
    glEnd()
    glEnable(GL_LIGHTING)

# ============================================================================
# UI RENDERING
# ============================================================================

def render_text(x, y, text):
    """Render 2D text"""
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_WIDTH, 0, WIN_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for char in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_hud():
    """Draw HUD"""
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    # Health
    glColor3f(1.0, 0.2, 0.2)
    render_text(25, WIN_HEIGHT - 35, f"Health: {int(game.health)}/{game.max_health}")
    
    # Health bar
    bar_w, bar_h = 220, 25
    health_ratio = game.health / game.max_health
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_WIDTH, 0, WIN_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # BG
    glColor3f(0.35, 0.0, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(25, WIN_HEIGHT - 65)
    glVertex2f(25 + bar_w, WIN_HEIGHT - 65)
    glVertex2f(25 + bar_w, WIN_HEIGHT - 65 - bar_h)
    glVertex2f(25, WIN_HEIGHT - 65 - bar_h)
    glEnd()
    
    # FG
    glColor3f(0.1, 1.0, 0.1)
    glBegin(GL_QUADS)
    glVertex2f(25, WIN_HEIGHT - 65)
    glVertex2f(25 + bar_w * health_ratio, WIN_HEIGHT - 65)
    glVertex2f(25 + bar_w * health_ratio, WIN_HEIGHT - 65 - bar_h)
    glVertex2f(25, WIN_HEIGHT - 65 - bar_h)
    glEnd()
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    # Stats
    glColor3f(1.0, 1.0, 0.3)
    render_text(25, WIN_HEIGHT - 105, f"Score: {game.score}")
    render_text(25, WIN_HEIGHT - 130, f"Level: {game.level}")
    render_text(25, WIN_HEIGHT - 155, f"Kills: {game.kills}")
    
    # Ammo
    glColor3f(0.3, 1.0, 1.0)
    render_text(25, WIN_HEIGHT - 185, f"Bullets: Unlimited")
    if game.weapon_unlocked:
        render_text(25, WIN_HEIGHT - 210, f"Missiles: {game.ammo_missiles}")
    
    # Weapon
    glColor3f(1.0, 1.0, 1.0)
    gun_name = "NORMAL GUN" if game.gun_type == 1 else "HEAVY GUN"
    render_text(WIN_WIDTH - 220, WIN_HEIGHT - 35, f"Gun: {gun_name}")
    if game.weapon_unlocked:
        render_text(WIN_WIDTH - 220, WIN_HEIGHT - 55, f"Missiles: {game.ammo_missiles}")
    
    # Difficulty
    glColor3f(0.85, 0.85, 0.85)
    render_text(WIN_WIDTH - 220, WIN_HEIGHT - 65, f"Difficulty: {game.difficulty.upper()}")
    
    # Camera
    cam_text = "3rd Person" if game.camera_mode == 'third' else "Cockpit"
    if game.show_rear_mirror:
        cam_text += " + Mirror"
    render_text(WIN_WIDTH - 220, WIN_HEIGHT - 95, f"Camera: {cam_text}")
    
    # Cheat
    if game.cheat_mode:
        glColor3f(1.0, 0.0, 0.0)
        render_text(WIN_WIDTH//2 - 100, WIN_HEIGHT - 35, "CHEAT MODE ACTIVE")
    
    # Invisibility status
    if game.invisibility_timer > 0:
        glColor3f(0.8, 0.2, 1.0)  # Purple
        seconds_left = game.invisibility_timer // 60
        render_text(WIN_WIDTH//2 - 80, WIN_HEIGHT - 60, f"INVISIBLE: {seconds_left}s")
    
    # PAUSE indicator
    if game.paused:
        glColor3f(1.0, 1.0, 0.0)  # Yellow
        render_text(WIN_WIDTH//2 - 60, WIN_HEIGHT//2 + 50, "GAME PAUSED")
        glColor3f(1.0, 1.0, 1.0)
        render_text(WIN_WIDTH//2 - 80, WIN_HEIGHT//2, "Press P to resume")
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def draw_rear_mirror():
    """Draw rear-view mirror"""
    if not game.show_rear_mirror:
        return
        
    mirror_w, mirror_h = 220, 165
    mirror_x = WIN_WIDTH - mirror_w - 25
    mirror_y = WIN_HEIGHT - mirror_h - 135
    
    glPushAttrib(GL_VIEWPORT_BIT)
    glViewport(mirror_x, mirror_y, mirror_w, mirror_h)
    
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluPerspective(65, mirror_w/mirror_h, 1, 120)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Look behind
    angle = math.radians(player.rotation_y + 180)
    look_x = player.x + math.sin(angle) * 6
    look_z = player.z + math.cos(angle) * 6
    gluLookAt(player.x, player.y + 1.5, player.z,
              look_x, player.y, look_z,
              0, 1, 0)
    
    glClear(GL_DEPTH_BUFFER_BIT)
    setup_lighting()
    draw_starfield()
    
    for enemy in enemies:
        if enemy.active:
            draw_enemy(enemy)
    for meteor in meteors:
        if meteor.active:
            draw_meteor(meteor)
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    glPopAttrib()
    glViewport(0, 0, WIN_WIDTH, WIN_HEIGHT)
    
    # Border
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WIN_WIDTH, 0, WIN_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    glColor3f(0.2, 1.0, 1.0)
    glLineWidth(4)
    glBegin(GL_LINE_LOOP)
    glVertex2f(mirror_x, mirror_y)
    glVertex2f(mirror_x + mirror_w, mirror_y)
    glVertex2f(mirror_x + mirror_w, mirror_y + mirror_h)
    glVertex2f(mirror_x, mirror_y + mirror_h)
    glEnd()
    
    glColor3f(0.2, 1.0, 1.0)
    glRasterPos2f(mirror_x + 65, mirror_y - 18)
    for char in "REAR VIEW":
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))
    
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def draw_menu():
    """Draw main menu"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    glColor3f(0.2, 1.0, 1.0)
    render_text(WIN_WIDTH//2 - 160, WIN_HEIGHT - 120, "SPACE SHOOTER 3D - PROFESSIONAL EDITION")
    
    glColor3f(1.0, 1.0, 1.0)
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 220, "Select Difficulty:")
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 260, "1 - Easy (Recommended)")
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 290, "2 - Medium")
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 320, "3 - Hard (Intense!)")
    
    glColor3f(0.2, 1.0, 0.2)
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 380, "Press SPACE to start")
    
    glColor3f(0.85, 0.85, 0.85)
    render_text(60, 180, "Controls:")
    render_text(60, 150, "WASD - Move | Mouse - Shoot | Arrow Keys - Pitch/Yaw")
    render_text(60, 120, "V - Camera | M - Mirror | Q - Switch Weapon | C - Cheat")
    render_text(60, 90, "P - Pause | R - Restart | ESC - Quit")
    
    glutSwapBuffers()
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

def draw_game_over():
    """Draw game over screen"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    glColor3f(1.0, 0.2, 0.2)
    render_text(WIN_WIDTH//2 - 110, WIN_HEIGHT - 180, "GAME OVER")
    
    glColor3f(1.0, 1.0, 0.3)
    render_text(WIN_WIDTH//2 - 160, WIN_HEIGHT - 280, f"Final Score: {game.score}")
    render_text(WIN_WIDTH//2 - 160, WIN_HEIGHT - 310, f"Level Reached: {game.level}")
    render_text(WIN_WIDTH//2 - 160, WIN_HEIGHT - 340, f"Enemies Defeated: {game.kills}")
    
    glColor3f(0.2, 1.0, 0.2)
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 410, "Press R to Restart")
    render_text(WIN_WIDTH//2 - 220, WIN_HEIGHT - 440, "Press ESC to Quit")
    
    glutSwapBuffers()
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)

# ============================================================================
# GAME LOGIC
# ============================================================================

def spawn_enemy():
    """Spawn enemy from ALL DIRECTIONS in 3D - different angles and positions"""
    # Choose spawn direction randomly from all around the player
    spawn_direction = random.choice(['front', 'back', 'left', 'right', 'above', 'below_front'])
    
    spawn_distance = random.uniform(80, 150)  # Distance from player
    
    if spawn_direction == 'front':
        # In front of player
        spawn_x = player.x + random.uniform(-60, 60)
        spawn_y = player.y + random.uniform(-15, 25)
        spawn_z = player.z - spawn_distance
    elif spawn_direction == 'back':
        # Behind player
        spawn_x = player.x + random.uniform(-60, 60)
        spawn_y = player.y + random.uniform(-10, 20)
        spawn_z = player.z + spawn_distance
    elif spawn_direction == 'left':
        # To the left
        spawn_x = player.x - spawn_distance
        spawn_y = player.y + random.uniform(-15, 25)
        spawn_z = player.z + random.uniform(-60, 60)
    elif spawn_direction == 'right':
        # To the right
        spawn_x = player.x + spawn_distance
        spawn_y = player.y + random.uniform(-15, 25)
        spawn_z = player.z + random.uniform(-60, 60)
    elif spawn_direction == 'above':
        # Above player (coming down)
        spawn_x = player.x + random.uniform(-50, 50)
        spawn_y = player.y + random.uniform(40, 70)
        spawn_z = player.z + random.uniform(-50, 50)
    else:  # below_front
        # Below and in front
        spawn_x = player.x + random.uniform(-50, 50)
        spawn_y = max(5, player.y - random.uniform(20, 40))
        spawn_z = player.z - random.uniform(60, 100)
    
    # Keep spawn within world bounds
    spawn_x = max(BOUNDARY_MIN + 30, min(BOUNDARY_MAX - 30, spawn_x))
    spawn_y = max(5, min(100, spawn_y))
    spawn_z = max(BOUNDARY_MIN + 30, min(BOUNDARY_MAX - 30, spawn_z))
    
    # Check if we should spawn a boss (every 20 kills: 20, 40, 60...)
    boss_threshold = ((game.kills // 20) * 20)
    if boss_threshold > 0 and boss_threshold not in game.boss_killed_at:
        # Check if there's no active boss already
        active_bosses = [e for e in enemies if e.type == 'boss' and e.active]
        if len(active_bosses) == 0:
            boss_tier = boss_threshold // 20
            game.boss_killed_at.add(boss_threshold)
            enemies.append(Enemy(spawn_x, spawn_y, spawn_z, 'boss', boss_tier))
            print(f"🔥 BOSS TIER {boss_tier} APPEARED!")
            print(f"   Health: {15 + (boss_tier - 1) * 5} bullets to kill")
            print(f"   Damage: {20 + (boss_tier - 1) * 10} per bullet")
            return
    
    enemies.append(Enemy(spawn_x, spawn_y, spawn_z, 'basic'))

def spawn_meteor():
    """Spawn meteor from ALL DIRECTIONS in 3D space"""
    # Choose spawn direction randomly
    spawn_direction = random.choice(['front', 'back', 'left', 'right', 'above', 'diagonal'])
    
    spawn_distance = random.uniform(60, 120)
    
    if spawn_direction == 'front':
        spawn_x = player.x + random.uniform(-50, 50)
        spawn_y = player.y + random.uniform(-10, 30)
        spawn_z = player.z - spawn_distance
    elif spawn_direction == 'back':
        spawn_x = player.x + random.uniform(-50, 50)
        spawn_y = player.y + random.uniform(-10, 30)
        spawn_z = player.z + spawn_distance
    elif spawn_direction == 'left':
        spawn_x = player.x - spawn_distance
        spawn_y = player.y + random.uniform(-10, 30)
        spawn_z = player.z + random.uniform(-50, 50)
    elif spawn_direction == 'right':
        spawn_x = player.x + spawn_distance
        spawn_y = player.y + random.uniform(-10, 30)
        spawn_z = player.z + random.uniform(-50, 50)
    elif spawn_direction == 'above':
        spawn_x = player.x + random.uniform(-40, 40)
        spawn_y = player.y + random.uniform(50, 80)
        spawn_z = player.z + random.uniform(-40, 40)
    else:  # diagonal
        angle = random.uniform(0, 360)
        spawn_x = player.x + math.cos(math.radians(angle)) * spawn_distance
        spawn_y = player.y + random.uniform(20, 50)
        spawn_z = player.z + math.sin(math.radians(angle)) * spawn_distance
    
    # Keep within bounds
    spawn_x = max(BOUNDARY_MIN + 20, min(BOUNDARY_MAX - 20, spawn_x))
    spawn_y = max(10, min(100, spawn_y))
    spawn_z = max(BOUNDARY_MIN + 20, min(BOUNDARY_MAX - 20, spawn_z))
    
    meteors.append(Meteor(spawn_x, spawn_y, spawn_z))

def spawn_black_hole():
    """Spawn black hole from ALL DIRECTIONS in 3D"""
    # 🔒 LIMIT: MAX 5 BLACK HOLES
    active_bh = [bh for bh in black_holes if bh.active]
    if len(active_bh) >= 5:
        return
    
    # Choose spawn direction randomly
    spawn_direction = random.choice(['front', 'left', 'right', 'above'])
    spawn_distance = random.uniform(70, 120)
    
    if spawn_direction == 'front':
        spawn_x = player.x + random.uniform(-40, 40)
        spawn_y = player.y + random.uniform(-5, 25)
        spawn_z = player.z - spawn_distance
    elif spawn_direction == 'left':
        spawn_x = player.x - spawn_distance
        spawn_y = player.y + random.uniform(-5, 20)
        spawn_z = player.z + random.uniform(-40, 40)
    elif spawn_direction == 'right':
        spawn_x = player.x + spawn_distance
        spawn_y = player.y + random.uniform(-5, 20)
        spawn_z = player.z + random.uniform(-40, 40)
    else:  # above
        spawn_x = player.x + random.uniform(-30, 30)
        spawn_y = player.y + random.uniform(40, 60)
        spawn_z = player.z + random.uniform(-30, 30)
    
    # Keep within bounds
    spawn_x = max(BOUNDARY_MIN + 20, min(BOUNDARY_MAX - 20, spawn_x))
    spawn_y = max(15, min(80, spawn_y))
    spawn_z = max(BOUNDARY_MIN + 20, min(BOUNDARY_MAX - 20, spawn_z))

    black_holes.append(BlackHole(spawn_x, spawn_y, spawn_z))


def spawn_powerup():
    # LIMIT: MAX 3 POWERUPS
    active_pu = [p for p in powerups if p.active]
    if len(active_pu) >= 3:
        return

    # Include invisibility powerup (rarer)
    ptype = random.choices(
        ['health', 'ammo', 'speed', 'invisibility'],
        weights=[30, 30, 25, 15]  # invisibility is rarer
    )[0]

    spawn_x = player.x + random.uniform(-25, 25)
    spawn_y = random.uniform(10, 18)
    spawn_z = player.z - random.uniform(45, 70)

    powerups.append(PowerUp(spawn_x, spawn_y, spawn_z, ptype))


def check_collisions():
    """Check all collisions"""
    # Bullets vs enemies
    for bullet in bullets[:]:
        if not bullet.active:
            continue
        for enemy in enemies[:]:
            if not enemy.active:
                continue
            dx = bullet.x - enemy.x
            dy = bullet.y - enemy.y
            dz = bullet.z - enemy.z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < enemy.size * 1.2:
                bullet.active = False
                # Use bullet's damage value
                if enemy.take_damage(bullet.damage):
                    explosions.append(Explosion(enemy.x, enemy.y, enemy.z, 
                                                enemy.size))
                    if enemy.type == 'boss':
                        game.score += 100 * enemy.boss_tier
                        print(f"💀 BOSS TIER {enemy.boss_tier} DEFEATED!")
                    else:
                        game.score += 10
                    game.kills += 1
                    
                    # Increase bullet speed every 10 kills
                    if game.kills % 10 == 0:
                        game.bullet_speed_bonus += 0.1
                        print("⚡ Bullet speed increased!")
                    
                    # Increase enemy count by 2 every 10 kills
                    enemy_increase_threshold = (game.kills // 10) * 10
                    if enemy_increase_threshold > game.last_enemy_increase:
                        game.enemies_per_wave += 2
                        game.last_enemy_increase = enemy_increase_threshold
                        print(f"⚠️ Enemy count increased! Now {game.enemies_per_wave} enemies per wave!")
                    
                    if game.weapon_unlocked:
                        game.ammo_missiles += 1
                    if game.kills % 5 == 0:
                        level_up()
                    # Check wave complete
                    active_enemies = [e for e in enemies if e.active]
                    if game.wave_spawned >= game.enemies_per_wave and \
                       len(active_enemies) == 0:
                        game.wave_number += 1
                        game.wave_spawned = 0
                        print(f"🌊 WAVE {game.wave_number} COMPLETE!")
                break
    
    # Enemy bullets vs player - BULLETS PERSIST AFTER ENEMY DEATH
    # Check invisibility - if invisible, enemies can't see/hit player
    for ebullet in enemy_bullets[:]:
        if not ebullet.active:
            continue
        dx = player.x - ebullet.x
        dy = player.y - ebullet.y
        dz = player.z - ebullet.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < 2.0:
            ebullet.active = False
            # CHEAT MODE: Invincible - no damage
            if game.cheat_mode:
                print("🛡️ BLOCKED by cheat mode!")
                continue
            # INVISIBILITY: Enemies can't see player - bullet passes through
            if game.invisibility_timer > 0:
                print("👻 Enemy bullet passed through - You're INVISIBLE!")
                continue
            # Calculate damage based on who fired
            if ebullet.boss_tier > 0:
                # Boss bullet: 20 for tier 1, 30 for tier 2, 40 for tier 3...
                damage = 20 + (ebullet.boss_tier - 1) * 10
            else:
                damage = 5  # Basic enemy damage
            game.health -= damage
            print(f"💥 Hit by enemy fire! -{damage} HP | Health: {game.health}")
    
    # Missiles vs enemies
    for missile in missiles[:]:
        if not missile.active:
            continue
        for enemy in enemies[:]:
            if not enemy.active:
                continue
            dx = missile.x - enemy.x
            dy = missile.y - enemy.y
            dz = missile.z - enemy.z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            if dist < 2.5:
                missile.active = False
                explosions.append(Explosion(missile.x, missile.y, missile.z, 1.5))
                for e in enemies:
                    if not e.active:
                        continue
                    ex_dist = math.sqrt((missile.x - e.x)**2 + (missile.y - e.y)**2 + (missile.z - e.z)**2)
                    if ex_dist < 4.0:
                        # Missile does 5 damage (1 missile = 5 bullets)
                        if e.take_damage(5):
                            explosions.append(Explosion(e.x, e.y, e.z, e.size))
                            game.score += 10 if e.type == 'basic' else 50
                            game.kills += 1
                            if e.type == 'boss':
                                print(f"💀 BOSS TIER {e.boss_tier} DEFEATED by missile!")
                            if game.kills % 5 == 0:
                                level_up()
                break
    
    # Player vs meteors
    for meteor in meteors[:]:
        if not meteor.active:
            continue
        dx = player.x - meteor.x
        dy = player.y - meteor.y
        dz = player.z - meteor.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < (meteor.size + 1.8):
            meteor.active = False
            explosions.append(Explosion(meteor.x, meteor.y, meteor.z, meteor.size))
            if not game.cheat_mode:  # Cheat mode: no damage
                game.health -= 15
            else:
                print("🛡️ Meteor blocked by cheat mode!")
    
    # Player vs enemies - INVISIBILITY makes player invisible to enemies
    for enemy in enemies[:]:
        if not enemy.active:
            continue
        dx = player.x - enemy.x
        dy = player.y - enemy.y
        dz = player.z - enemy.z
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        if dist < 3.5:
            enemy.active = False
            explosions.append(Explosion(enemy.x, enemy.y, enemy.z, enemy.size))
            if game.cheat_mode:
                print("🛡️ Enemy collision blocked by cheat mode!")
            elif game.invisibility_timer > 0:
                print("👻 Enemy passed through - You're INVISIBLE!")
            else:
                game.health -= 12

def level_up():
    """Level up"""
    game.level += 1
    if game.level == 2 and not game.weapon_unlocked:
        game.weapon_unlocked = True
        game.ammo_missiles = 5
    game.max_health += 10
    game.health = min(game.max_health, game.health + 25)

def update_game():
    """Main game update"""
    if game.state != STATE_PLAYING or game.paused:
        return
    
    # Black hole death animation
    if game.in_black_hole_death:
        game.death_animation_timer -= 1
        # Pull player toward black hole center
        for bh in black_holes:
            if bh.active:
                dx = bh.x - player.x
                dy = bh.y - player.y
                dz = bh.z - player.z
                player.x += dx * 0.05
                player.y += dy * 0.05
                player.z += dz * 0.05
        if game.death_animation_timer <= 0:
            print("🌀 SUCKED INTO BLACK HOLE! Restarting...")
            game.state = STATE_MENU
            reset_game()
        return
        
    if game.health <= 0:
        game.state = STATE_GAME_OVER
        return
    
    game.frame_count += 1
    
    # Update invisibility timer
    if game.invisibility_timer > 0:
        game.invisibility_timer -= 1
        # Notify when invisibility ends
        if game.invisibility_timer == 0:
            print("👁️ Invisibility ended - Enemies can see you again!")
        elif game.invisibility_timer == 60:  # 1 second warning
            print("⚠️ Invisibility ending in 1 second!")
    
    # CHEAT MODE: Auto-fire at enemies
    if game.cheat_mode and game.frame_count % 3 == 0:  # Fire every 3 frames
        active_enemies = [e for e in enemies if e.active]
        if active_enemies:
            # Find closest enemy
            closest = min(active_enemies, 
                         key=lambda e: math.sqrt((e.x-player.x)**2 + (e.z-player.z)**2))
            # Fire bullet toward closest enemy
            dx = closest.x - player.x
            dz = closest.z - player.z
            angle = math.degrees(math.atan2(dx, dz))
            spawn_x = player.x + math.sin(math.radians(angle)) * 2.5
            spawn_z = player.z + math.cos(math.radians(angle)) * 2.5
            bullets.append(Bullet(spawn_x, player.y, spawn_z, angle))
    
    # Update player
    player.update()
    
    # Update projectiles
    for bullet in bullets:
        bullet.update()
    bullets[:] = [b for b in bullets if b.active]
    
    for missile in missiles:
        missile.update()
    missiles[:] = [m for m in missiles if m.active]
    
    # Update enemy bullets
    for ebullet in enemy_bullets:
        ebullet.update()
    enemy_bullets[:] = [eb for eb in enemy_bullets if eb.active]
    
    # Update enemies
    for enemy in enemies:
        if enemy.active:
            enemy.update()
    enemies[:] = [e for e in enemies if e.active]
    
    # Update obstacles
    for meteor in meteors:
        if meteor.active:
            meteor.update()
    meteors[:] = [m for m in meteors if m.active]
    
    for bh in black_holes:
        if bh.active:
            bh.update()
    black_holes[:] = [bh for bh in black_holes if bh.active]
    
    for pu in powerups:
        if pu.active:
            pu.update()
    powerups[:] = [pu for pu in powerups if pu.active]
    
    # Update explosions
    for exp in explosions:
        if exp.active:
            exp.update()
    explosions[:] = [e for e in explosions if e.active]
    
    # Collisions
    check_collisions()
    
    # Wave-based spawning - CONTINUOUS but slower
    # Always spawn enemies if we haven't reached wave limit
    if game.wave_spawned < game.enemies_per_wave:
        if game.frame_count % 80 == 0:  # Spawn every ~1.3 seconds (slower)
            spawn_enemy()
            game.wave_spawned += 1
    else:
        # Wave complete - check if all enemies dead
        active_enemies = [e for e in enemies if e.active]
        if len(active_enemies) == 0:
            # Start new wave
            game.wave_number += 1
            game.wave_spawned = 0
            print(f"🌊 WAVE {game.wave_number} STARTING!")
    
    # Meteor spawning - even less frequent
    game.meteor_timer += 1
    if game.meteor_timer > 450:  # Much slower meteor spawning (was 300)
        spawn_meteor()
        game.meteor_timer = 0
    
    # Black hole spawning - rare
    if game.frame_count % 1800 == 0 and random.random() < 0.25:
        spawn_black_hole()
    
    # Powerup spawning
    game.powerup_timer += 1
    if game.powerup_timer > 500:
        spawn_powerup()
        game.powerup_timer = 0
    
    # Cooldowns
    if game.fire_cooldown > 0:
        game.fire_cooldown -= 1
    if game.missile_cooldown > 0:
        game.missile_cooldown -= 1

def setup_camera():
    """Setup camera view"""
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(65, WIN_WIDTH/WIN_HEIGHT, 0.1, 800)  # Increased far plane for bigger world
    
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    if game.camera_mode == 'third':
        # Third person - slightly further back for better view
        cam_dist = 15
        cam_height = 7
        angle = math.radians(player.rotation_y)
        cam_x = player.x - math.sin(angle) * cam_dist
        cam_z = player.z - math.cos(angle) * cam_dist
        cam_y = player.y + cam_height
        
        gluLookAt(cam_x, cam_y, cam_z,
                  player.x, player.y, player.z,
                  0, 1, 0)
    else:
        # First person
        angle = math.radians(player.rotation_y)
        look_x = player.x + math.sin(angle) * 25
        look_z = player.z + math.cos(angle) * 25
        
        gluLookAt(player.x, player.y + 1.0, player.z,
                  look_x, player.y, look_z,
                  0, 1, 0)

def render():
    """Main render function"""
    if game.state == STATE_MENU:
        draw_menu()
        return
    
    if game.state == STATE_GAME_OVER:
        draw_game_over()
        return
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    setup_camera()
    setup_lighting()
    
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    
    # Draw scene
    draw_skybox()
    draw_starfield()
    draw_grid()
    
    for meteor in meteors:
        if meteor.active:
            draw_meteor(meteor)
    
    for bh in black_holes:
        if bh.active:
            draw_black_hole(bh)
    
    for pu in powerups:
        if pu.active:
            draw_powerup(pu)
    
    for enemy in enemies:
        if enemy.active:
            draw_enemy(enemy)
    
    for bullet in bullets:
        if bullet.active:
            draw_bullet(bullet)
    
    for missile in missiles:
        if missile.active:
            draw_missile(missile)
    
    for ebullet in enemy_bullets:
        if ebullet.active:
            draw_enemy_bullet(ebullet)
    
    for exp in explosions:
        if exp.active:
            draw_explosion(exp)
    
    if game.camera_mode != 'first':
        draw_spaceship()
    
    draw_hud()
    
    if game.show_rear_mirror:
        draw_rear_mirror()
    
    glutSwapBuffers()

def idle_func():
    """Idle callback"""
    update_game()
    glutPostRedisplay()

def keyboard_handler(key, x, y):
    """Keyboard input"""
    if game.state == STATE_MENU:
        if key == b' ':
            game.state = STATE_PLAYING
            init_game()
        elif key == b'1':
            game.difficulty = 'easy'
        elif key == b'2':
            game.difficulty = 'medium'
        elif key == b'3':
            game.difficulty = 'hard'
        elif key == b'\x1b':
            glutLeaveMainLoop()
        glutPostRedisplay()
        return
    
    if game.state == STATE_GAME_OVER:
        if key == b'r' or key == b'R':
            game.state = STATE_MENU
            reset_game()
        elif key == b'\x1b':
            glutLeaveMainLoop()
        glutPostRedisplay()
        return
    
    if game.state == STATE_PLAYING:
        # PAUSE functionality - P key
        if key == b'p' or key == b'P':
            game.paused = not game.paused
            if game.paused:
                print("⏸️ GAME PAUSED - Press P to resume")
            else:
                print("▶️ GAME RESUMED")
            glutPostRedisplay()
            return
        
        # Don't process other keys if paused
        if game.paused:
            glutPostRedisplay()
            return
            
        if key == b'w' or key == b'W':
            player.move_forward()
        elif key == b's' or key == b'S':
            player.move_backward()
        elif key == b'a' or key == b'A':
            player.move_left()
        elif key == b'd' or key == b'D':
            player.move_right()
        elif key == b'v' or key == b'V':
            game.camera_mode = 'first' if game.camera_mode == 'third' else 'third'
        elif key == b'm' or key == b'M':
            game.show_rear_mirror = not game.show_rear_mirror
        elif key == b'q' or key == b'Q':
            # Toggle gun type (1 = normal, 2 = heavy)
            game.gun_type = 2 if game.gun_type == 1 else 1
            gun_name = "NORMAL GUN" if game.gun_type == 1 else "HEAVY GUN"
            print(f"🔫 Switched to {gun_name}!")
        elif key == b'c' or key == b'C':
            game.cheat_mode = not game.cheat_mode
        elif key == b'r' or key == b'R':
            game.state = STATE_MENU
            reset_game()
        elif key == b'\x1b':
            glutLeaveMainLoop()
        
        glutPostRedisplay()

def special_keys_handler(key, x, y):
    """Special keys"""
    if game.state != STATE_PLAYING:
        return
    
    if key == GLUT_KEY_UP:
        player.move_up()
    elif key == GLUT_KEY_DOWN:
        player.move_down()
    elif key == GLUT_KEY_LEFT:
        player.rotate_left()
    elif key == GLUT_KEY_RIGHT:
        player.rotate_right()
    
    glutPostRedisplay()

def mouse_handler(button, state, x, y):
    """Mouse input"""
    if game.state != STATE_PLAYING or state != GLUT_DOWN:
        return
    
    if button == GLUT_LEFT_BUTTON:
        if game.fire_cooldown == 0:
            angle = math.radians(player.rotation_y)
            spawn_x = player.x + math.sin(angle) * 2.5
            spawn_z = player.z + math.cos(angle) * 2.5
            bullets.append(Bullet(spawn_x, player.y, spawn_z, 
                                  player.rotation_y, game.gun_type))
            # Heavy gun has longer cooldown
            game.fire_cooldown = 4 if game.gun_type == 1 else 8
    
    elif button == GLUT_RIGHT_BUTTON:
        if game.weapon_unlocked and game.missile_cooldown == 0:
            if game.ammo_missiles > 0:
                # Find target
                target = None
                if enemies:
                    active_enemies = [e for e in enemies if e.active]
                    if active_enemies:
                        if game.cheat_mode:
                            target = min(active_enemies,
                                       key=lambda e: math.sqrt((e.x-player.x)**2 + (e.z-player.z)**2))
                        else:
                            front_enemies = [e for e in active_enemies if e.z < player.z]
                            if front_enemies:
                                target = min(front_enemies,
                                           key=lambda e: math.sqrt((e.x-player.x)**2 + (e.z-player.z)**2))
                
                angle = math.radians(player.rotation_y)
                spawn_x = player.x + math.sin(angle) * 2.5
                spawn_z = player.z + math.cos(angle) * 2.5
                missiles.append(Missile(spawn_x, player.y, spawn_z, player.rotation_y, target))
                game.ammo_missiles -= 1
                game.missile_cooldown = 28
    
    glutPostRedisplay()

def init_game():
    """Initialize game"""
    global enemies, bullets, missiles, meteors, black_holes, powerups, explosions, stars
    
    enemies.clear()
    bullets.clear()
    missiles.clear()
    meteors.clear()
    black_holes.clear()
    powerups.clear()
    explosions.clear()
    
    # Reset player
    player.x = 0
    player.y = 12
    player.z = 0
    player.rotation_y = 0
    player.rotation_z = 0
    player.vx = 0
    player.vy = 0
    player.vz = 0
    
    # Generate stars - many more stars for bigger world
    stars.clear()
    for _ in range(800):
        stars.append((
            random.uniform(-WORLD_SIZE*3, WORLD_SIZE*3),
            random.uniform(-20, 150),
            random.uniform(-WORLD_SIZE*3, WORLD_SIZE*3)
        ))
    
    # Initialize wave system
    game.wave_number = 1
    game.enemies_per_wave = 5
    game.wave_spawned = 0
    
    # Spawn initial wave
    print(f"🌊 WAVE 1 STARTING! Enemies: {game.enemies_per_wave}")
    
    game.frame_count = 0
    game.spawn_timer = 0
    game.meteor_timer = 0
    game.powerup_timer = 0

def reset_game():
    """Reset game state"""
    game.health = 100
    game.max_health = 100
    game.score = 0
    game.level = 1
    game.kills = 0
    game.ammo_missiles = 0
    game.weapon_unlocked = False
    game.current_weapon = 'primary'
    game.gun_type = 1
    game.bullet_speed_bonus = 0
    game.fire_cooldown = 0
    game.missile_cooldown = 0
    game.camera_mode = 'third'
    game.show_rear_mirror = False
    game.cheat_mode = False
    game.spawn_timer = 0
    game.meteor_timer = 0
    game.powerup_timer = 0
    game.wave_number = 1
    game.enemies_per_wave = 5
    game.wave_spawned = 0
    game.in_black_hole_death = False
    game.death_animation_timer = 0
    game.boss_killed_at = set()
    game.invisibility_timer = 0
    game.last_enemy_increase = 0

def init_opengl():
    """Initialize OpenGL"""
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_POINT_SMOOTH)
    glEnable(GL_LINE_SMOOTH)
    glShadeModel(GL_SMOOTH)

def reshape_handler(width, height):
    """Window reshape"""
    global WIN_WIDTH, WIN_HEIGHT
    WIN_WIDTH = width
    WIN_HEIGHT = height
    glViewport(0, 0, width, height)

def main():
    """Main entry point"""
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WIN_WIDTH, WIN_HEIGHT)
    glutInitWindowPosition(50, 50)
    glutCreateWindow(b"Space Shooter 3D - Professional Edition")
    
    init_opengl()
    
    glutDisplayFunc(render)
    glutIdleFunc(idle_func)
    glutKeyboardFunc(keyboard_handler)
    glutSpecialFunc(special_keys_handler)
    glutMouseFunc(mouse_handler)
    glutReshapeFunc(reshape_handler)
    
    print("=" * 70)
    print("           SPACE SHOOTER 3D - PROFESSIONAL EDITION")
    print("=" * 70)
    print("Welcome to the ultimate space combat experience!")
    print("")
    print("Features:")
    print("  • Dual weapon system (Bullets + Homing Missiles)")
    print("  • 3 difficulty levels")
    print("  • Multiple camera modes + rear-view mirror")
    print("  • Dynamic enemies with health bars")
    print("  • Meteors, black holes, and power-ups")
    print("  • Leveling system with progression")
    print("  • Cheat mode for auto-aim")
    print("  • Particle explosions and visual effects")
    print("  • Professional lighting system")
    print("")
    print("Select difficulty (1/2/3) and press SPACE to begin!")
    print("=" * 70)
    
    glutMainLoop()

if __name__ == "__main__":
    main()
