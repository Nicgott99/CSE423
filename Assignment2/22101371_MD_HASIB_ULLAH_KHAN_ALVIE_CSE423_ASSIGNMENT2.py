"""
CSE423 Lab 02: Catch the Diamonds
Midpoint Line Drawing Algorithm Implementation
Student: MD HASIB ULLAH KHAN ALVIE
ID: 22101371
Section: 10
"""

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import time

# Window dimensions
WIN_WIDTH = 800
WIN_HEIGHT = 600

# Game state
class GameState:
    def __init__(self):
        self.score = 0
        self.playing = True
        self.paused = False
        self.auto_mode = False
        self.game_over = False
        
state = GameState()

# Diamond properties
class Diamond:
    def __init__(self):
        self.x = random.randint(80, WIN_WIDTH - 80)
        self.y = WIN_HEIGHT - 80
        self.size = 18
        self.speed = 1.8
        self.color = self.random_color()
    
    def random_color(self):
        colors = [
            (1.0, 0.3, 0.6),  # Pink
            (0.3, 1.0, 0.9),  # Cyan
            (1.0, 0.9, 0.2),  # Yellow
            (0.6, 0.3, 1.0),  # Purple
            (0.3, 1.0, 0.5),  # Green
        ]
        return random.choice(colors)
    
    def reset(self):
        self.x = random.randint(80, WIN_WIDTH - 80)
        self.y = WIN_HEIGHT - 80
        self.color = self.random_color()

diamond = Diamond()

# Catcher properties
class Catcher:
    def __init__(self):
        self.x = WIN_WIDTH // 2
        self.y = 60
        self.width = 90
        self.height = 25
        self.speed = 18
        self.color = (1.0, 1.0, 1.0)
    
    def get_bounds(self):
        half_w = self.width // 2
        return {
            'left': self.x - half_w,
            'right': self.x + half_w,
            'top': self.y + self.height,
            'bottom': self.y
        }

catcher = Catcher()

# Time tracking
prev_time = time.time()

# Button regions
btn_restart = {'x': 40, 'y': WIN_HEIGHT - 50, 'size': 45}
btn_toggle = {'x': WIN_WIDTH // 2 - 22, 'y': WIN_HEIGHT - 50, 'size': 45}
btn_exit = {'x': WIN_WIDTH - 85, 'y': WIN_HEIGHT - 50, 'size': 45}


# ============ MIDPOINT LINE ALGORITHM ============

def get_zone(dx, dy):
    """Identify which of 8 zones the line belongs to"""
    if abs(dx) >= abs(dy):
        if dx >= 0 and dy >= 0:
            return 0
        elif dx < 0 and dy >= 0:
            return 3
        elif dx < 0 and dy < 0:
            return 4
        else:
            return 7
    else:
        if dx >= 0 and dy >= 0:
            return 1
        elif dx < 0 and dy >= 0:
            return 2
        elif dx < 0 and dy < 0:
            return 5
        else:
            return 6


def zone_to_zero(x, y, z):
    """Map point from zone z to zone 0"""
    if z == 0:
        return x, y
    elif z == 1:
        return y, x
    elif z == 2:
        return y, -x
    elif z == 3:
        return -x, y
    elif z == 4:
        return -x, -y
    elif z == 5:
        return -y, -x
    elif z == 6:
        return -y, x
    elif z == 7:
        return x, -y


def zero_to_zone(x, y, z):
    """Map point from zone 0 back to zone z"""
    if z == 0:
        return x, y
    elif z == 1:
        return y, x
    elif z == 2:
        return -y, x
    elif z == 3:
        return -x, y
    elif z == 4:
        return -x, -y
    elif z == 5:
        return -y, -x
    elif z == 6:
        return y, -x
    elif z == 7:
        return x, -y


def midpoint_line(x1, y1, x2, y2):
    """Draw line using midpoint algorithm - only GL_POINTS allowed"""
    dx = x2 - x1
    dy = y2 - y1
    
    zone = get_zone(dx, dy)
    
    # Convert to zone 0
    px1, py1 = zone_to_zero(x1, y1, zone)
    px2, py2 = zone_to_zero(x2, y2, zone)
    
    # Zone 0 calculations
    dx0 = px2 - px1
    dy0 = py2 - py1
    
    d = 2 * dy0 - dx0
    incr_e = 2 * dy0
    incr_ne = 2 * (dy0 - dx0)
    
    y = py1
    
    glBegin(GL_POINTS)
    for x in range(px1, px2 + 1):
        # Convert back and draw
        orig_x, orig_y = zero_to_zone(x, y, zone)
        glVertex2f(orig_x, orig_y)
        
        if d > 0:
            y += 1
            d += incr_ne
        else:
            d += incr_e
    glEnd()


# ============ DRAWING FUNCTIONS ============

def draw_diamond(cx, cy, s):
    """Draw diamond shape"""
    # Four vertices
    top = (cx, cy + s)
    right = (cx + s, cy)
    bottom = (cx, cy - s)
    left = (cx - s, cy)
    
    # Draw four edges
    midpoint_line(int(top[0]), int(top[1]), int(right[0]), int(right[1]))
    midpoint_line(int(right[0]), int(right[1]), int(bottom[0]), int(bottom[1]))
    midpoint_line(int(bottom[0]), int(bottom[1]), int(left[0]), int(left[1]))
    midpoint_line(int(left[0]), int(left[1]), int(top[0]), int(top[1]))


def draw_catcher_bowl(cx, cy, w, h):
    """Draw catcher shape"""
    # Bowl vertices (trapezoid)
    tl = (cx - w // 2, cy + h)
    tr = (cx + w // 2, cy + h)
    br = (cx + w // 2 - 12, cy)
    bl = (cx - w // 2 + 12, cy)
    
    midpoint_line(int(tl[0]), int(tl[1]), int(tr[0]), int(tr[1]))
    midpoint_line(int(tr[0]), int(tr[1]), int(br[0]), int(br[1]))
    midpoint_line(int(br[0]), int(br[1]), int(bl[0]), int(bl[1]))
    midpoint_line(int(bl[0]), int(bl[1]), int(tl[0]), int(tl[1]))


def draw_left_arrow(x, y, sz):
    """Draw restart button (left arrow)"""
    cx = x + sz // 2
    cy = y + sz // 2
    a = sz // 3
    
    tip = (cx - a, cy)
    top_r = (cx + a, cy + a)
    bot_r = (cx + a, cy - a)
    
    midpoint_line(int(tip[0]), int(tip[1]), int(top_r[0]), int(top_r[1]))
    midpoint_line(int(tip[0]), int(tip[1]), int(bot_r[0]), int(bot_r[1]))
    midpoint_line(int(top_r[0]), int(top_r[1]), int(bot_r[0]), int(bot_r[1]))


def draw_play_triangle(x, y, sz):
    """Draw play icon"""
    cx = x + sz // 2
    cy = y + sz // 2
    a = sz // 3
    
    left = (cx - a, cy - a)
    right = (cx + a, cy)
    bottom = (cx - a, cy + a)
    
    midpoint_line(int(left[0]), int(left[1]), int(right[0]), int(right[1]))
    midpoint_line(int(right[0]), int(right[1]), int(bottom[0]), int(bottom[1]))
    midpoint_line(int(bottom[0]), int(bottom[1]), int(left[0]), int(left[1]))


def draw_pause_bars(x, y, sz):
    """Draw pause icon"""
    cx = x + sz // 2
    cy = y + sz // 2
    bar_w = sz // 7
    bar_h = sz // 2
    gap = sz // 10
    
    # Left bar
    lx = cx - gap - bar_w
    midpoint_line(lx, cy - bar_h // 2, lx, cy + bar_h // 2)
    midpoint_line(lx + bar_w, cy - bar_h // 2, lx + bar_w, cy + bar_h // 2)
    midpoint_line(lx, cy - bar_h // 2, lx + bar_w, cy - bar_h // 2)
    midpoint_line(lx, cy + bar_h // 2, lx + bar_w, cy + bar_h // 2)
    
    # Right bar
    rx = cx + gap
    midpoint_line(rx, cy - bar_h // 2, rx, cy + bar_h // 2)
    midpoint_line(rx + bar_w, cy - bar_h // 2, rx + bar_w, cy + bar_h // 2)
    midpoint_line(rx, cy - bar_h // 2, rx + bar_w, cy - bar_h // 2)
    midpoint_line(rx, cy + bar_h // 2, rx + bar_w, cy + bar_h // 2)


def draw_cross(x, y, sz):
    """Draw exit icon (X)"""
    cx = x + sz // 2
    cy = y + sz // 2
    a = sz // 3
    
    midpoint_line(cx - a, cy - a, cx + a, cy + a)
    midpoint_line(cx - a, cy + a, cx + a, cy - a)


# ============ COLLISION DETECTION ============

def check_collision():
    """AABB collision detection between diamond and catcher"""
    # Diamond bounding box
    d_left = diamond.x - diamond.size
    d_right = diamond.x + diamond.size
    d_top = diamond.y + diamond.size
    d_bottom = diamond.y - diamond.size
    
    # Catcher bounding box
    c_bounds = catcher.get_bounds()
    
    # AABB collision
    return (d_left < c_bounds['right'] and
            d_right > c_bounds['left'] and
            d_bottom < c_bounds['top'] and
            d_top > c_bounds['bottom'])


# ============ GAME LOGIC ============

def update_game():
    """Update game state with delta time"""
    global prev_time
    
    # Always request redraw
    glutPostRedisplay()
    
    # If paused, don't update game logic
    if state.paused:
        return
    
    # If game over, stop everything
    if state.game_over:
        return
    
    # Calculate delta time for frame-independent movement
    curr_time = time.time()
    dt = curr_time - prev_time
    prev_time = curr_time
    
    # Auto mode - smooth movement
    if state.auto_mode and state.playing:
        diff = diamond.x - catcher.x
        if abs(diff) > 8:
            if diff > 0:
                catcher.x += min(catcher.speed, diff)
            else:
                catcher.x -= min(catcher.speed, abs(diff))
        
        # Boundary check
        half_w = catcher.width // 2
        if catcher.x < half_w + 10:
            catcher.x = half_w + 10
        elif catcher.x > WIN_WIDTH - half_w - 10:
            catcher.x = WIN_WIDTH - half_w - 10
    
    # Move diamond down continuously using delta time
    # This ensures consistent speed across different frame rates
    diamond.y -= diamond.speed * 60 * dt  # Normalized for ~60 FPS
    
    # Check collision with catcher (CAUGHT the diamond)
    if check_collision():
        state.score += 1
        print(f"Score: {state.score}")
        diamond.speed += 0.08  # Increase difficulty gradually
        diamond.reset()  # Spawn new diamond immediately at top
    
    # Check if MISSED (diamond fell below catcher bottom) - GAME OVER
    elif diamond.y + diamond.size < catcher.y:
        state.game_over = True
        state.playing = False
        catcher.color = (1.0, 0.0, 0.0)
        print(f"Game Over! You missed a diamond! Final Score: {state.score}")


def restart_game():
    """Reset game to initial state"""
    global prev_time
    state.score = 0
    state.playing = True
    state.paused = False
    state.game_over = False
    state.auto_mode = False
    diamond.speed = 1.8
    diamond.reset()
    catcher.x = WIN_WIDTH // 2
    catcher.color = (1.0, 1.0, 1.0)
    prev_time = time.time()
    print("Starting Over")


# ============ INPUT HANDLERS ============

def on_mouse(button, action, x, y):
    """Handle mouse clicks"""
    if button == GLUT_LEFT_BUTTON and action == GLUT_DOWN:
        y = WIN_HEIGHT - y  # Flip Y coordinate
        
        # Check restart button
        if (btn_restart['x'] <= x <= btn_restart['x'] + btn_restart['size'] and
            btn_restart['y'] <= y <= btn_restart['y'] + btn_restart['size']):
            restart_game()
        
        # Check toggle button
        elif (btn_toggle['x'] <= x <= btn_toggle['x'] + btn_toggle['size'] and
              btn_toggle['y'] <= y <= btn_toggle['y'] + btn_toggle['size']):
            state.paused = not state.paused
            print("Paused" if state.paused else "Resumed")
        
        # Check exit button
        elif (btn_exit['x'] <= x <= btn_exit['x'] + btn_exit['size'] and
              btn_exit['y'] <= y <= btn_exit['y'] + btn_exit['size']):
            print(f"Goodbye! Final Score: {state.score}")
            glutLeaveMainLoop()


def on_keyboard(key, x, y):
    """Handle keyboard input"""
    if key == b'c' or key == b'C':
        state.auto_mode = not state.auto_mode
        print("Cheat Mode: " + ("ON" if state.auto_mode else "OFF"))


def on_special(key, x, y):
    """Handle arrow keys"""
    # Don't move if game is over, but ALLOW movement when paused is removed
    if state.game_over:
        return
    
    # Don't move when paused
    if state.paused:
        return
    
    half_w = catcher.width // 2
    
    if key == GLUT_KEY_LEFT:
        catcher.x -= catcher.speed
        if catcher.x < half_w + 10:
            catcher.x = half_w + 10
    
    elif key == GLUT_KEY_RIGHT:
        catcher.x += catcher.speed
        if catcher.x > WIN_WIDTH - half_w - 10:
            catcher.x = WIN_WIDTH - half_w - 10


# ============ RENDERING ============

def render():
    """Main render function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glPointSize(2)
    
    # Draw buttons
    glColor3f(0.0, 0.9, 0.9)  # Teal
    draw_left_arrow(btn_restart['x'], btn_restart['y'], btn_restart['size'])
    
    glColor3f(1.0, 0.75, 0.0)  # Amber
    if state.paused:
        draw_play_triangle(btn_toggle['x'], btn_toggle['y'], btn_toggle['size'])
    else:
        draw_pause_bars(btn_toggle['x'], btn_toggle['y'], btn_toggle['size'])
    
    glColor3f(1.0, 0.0, 0.0)  # Red
    draw_cross(btn_exit['x'], btn_exit['y'], btn_exit['size'])
    
    # Draw diamond (if active)
    if state.playing or state.paused:
        glColor3f(*diamond.color)
        draw_diamond(int(diamond.x), int(diamond.y), diamond.size)
    
    # Draw catcher
    glColor3f(*catcher.color)
    draw_catcher_bowl(int(catcher.x), catcher.y, catcher.width, catcher.height)
    
    glutSwapBuffers()


def init_viewport():
    """Setup OpenGL viewport"""
    glViewport(0, 0, WIN_WIDTH, WIN_HEIGHT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0.0, WIN_WIDTH, 0.0, WIN_HEIGHT, 0.0, 1.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


# ============ MAIN ============

def main():
    """Program entry point"""
    glutInit()
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(WIN_WIDTH, WIN_HEIGHT)
    glutInitWindowPosition(120, 120)
    glutCreateWindow(b"CSE423 Lab 02 - Catch the Diamonds")
    
    glClearColor(0.0, 0.0, 0.0, 1.0)
    init_viewport()
    
    glutDisplayFunc(render)
    glutIdleFunc(update_game)
    glutMouseFunc(on_mouse)
    glutKeyboardFunc(on_keyboard)
    glutSpecialFunc(on_special)
    
    print("=" * 40)
    print("   CATCH THE DIAMONDS")
    print("=" * 40)
    print("Controls:")
    print("  LEFT/RIGHT Arrow - Move catcher")
    print("  C - Toggle auto mode")
    print("  Click buttons to control game")
    print("\nGame Started!")
    print("=" * 40)
    
    glutMainLoop()


if __name__ == "__main__":
    main()
