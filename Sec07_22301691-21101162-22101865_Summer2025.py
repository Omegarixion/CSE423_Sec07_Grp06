from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# Player state
player_pos = [0.0, 0.0, 50.0]
player_rotation_y = 0.0
player_speed = 5.0
player_yaw_speed = 3.0

# Movement flags
move_forward = False
move_backward = False
strafe_left = False
strafe_right = False

# Camera system
camera_mode = 0  
third_person_offset = [0, -150, 100]

# Weapon system
weapon_fire_rate = 0.2
ammo_count = 30
max_ammo = 30
infinite_ammo = False
last_shot_time = 0.0

# Bullet system
bullets = []
bullet_speed = 50.0
bullet_lifetime = 3.0
bullet_type = 0  
# Scoring system
score = 0
score_effects = []

# Enemy system
enemies = []
enemy_spawn_timer = 0.0
enemy_spawn_rate = 2.0

# Game state
game_health = 100
game_lives = 3
game_over = False

# Checkpoint system
checkpoint_data = {
    'player_pos': list(player_pos),
    'player_rotation_y': player_rotation_y,
    'camera_mode': camera_mode
}

# Trigger zones
trigger_zones = {
    'spawn_area_1': {'bounds': (-200, 200, -200, 200, 0, 100), 'activated': False, 'message': "Enemy wave 1 activated!"},
    'hazard_zone_1': {'bounds': (300, 500, 300, 500, 0, 100), 'activated': False, 'message': "Hazard trap sprung!"}
}

# Cheat features
god_mode_active = False
freeze_enemies = False

# Game constants
fovY = 60
GRID_LENGTH = 600

class Bullet:
    def __init__(self, x, y, z, direction_x, direction_y, direction_z):
        self.x = x
        self.y = y
        self.z = z
        self.direction_x = direction_x
        self.direction_y = direction_y
        self.direction_z = direction_z
        self.speed = bullet_speed
        self.lifetime = bullet_lifetime
        self.spawn_time = time.time()
        self.trail_positions = []
    
    def update(self, delta_time):
        self.trail_positions.append((self.x, self.y, self.z))
        if len(self.trail_positions) > 5:
            self.trail_positions.pop(0)
        
        self.x += self.direction_x * self.speed * delta_time
        self.y += self.direction_y * self.speed * delta_time
        self.z += self.direction_z * self.speed * delta_time
        
        if (abs(self.x) > GRID_LENGTH or abs(self.y) > GRID_LENGTH or 
            self.z < 0 or self.z > 200):
            return False
        
        if time.time() - self.spawn_time > self.lifetime:
            return False
        
        return True

class Enemy:
    def __init__(self, x, y, z, enemy_type="static"):
        self.x = x
        self.y = y
        self.z = z
        self.enemy_type = enemy_type
        self.health = 3
        self.size = 30
        self.color = (1.0, 0.0, 0.0) if enemy_type == "static" else (0.0, 1.0, 0.0)
        self.speed = 0.0 if enemy_type == "static" else 2.0
    
    def take_damage(self):
        self.health -= 1
        return self.health <= 0
    
    def update(self, delta_time):
        if freeze_enemies:
            return
        
        if self.enemy_type == "charger":
            dx = player_pos[0] - self.x
            dy = player_pos[1] - self.y
            dist = math.sqrt(dx*dx + dy*dy) + 1e-6
            step = min(self.speed, dist)
            self.x += (dx/dist) * step
            self.y += (dy/dist) * step
    
    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glColor3f(*self.color)
        glutSolidCube(self.size)
        glPopMatrix()

class ScoreEffect:
    def __init__(self, x, y, points):
        self.x = x
        self.y = y
        self.points = points
        self.spawn_time = time.time()
        self.lifetime = 2.0
    
    def update(self):
        return time.time() - self.spawn_time <= self.lifetime
    
    def draw(self):
        age = time.time() - self.spawn_time
        alpha = 1.0 - (age / self.lifetime)
        y_offset = age * 50
        
        glColor4f(1.0, 1.0, 0.0, alpha)
        draw_text(self.x, self.y + y_offset, f"+{self.points}", 
                 font=GLUT_BITMAP_HELVETICA_12, color=(1.0, 1.0, 0.0))

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1, 1, 1)):
    glColor3f(*color)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_bullets():
    glPushMatrix()
    for bullet in bullets:
        if len(bullet.trail_positions) > 1:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            for i, (trail_x, trail_y, trail_z) in enumerate(bullet.trail_positions):
                alpha = (i + 1) / len(bullet.trail_positions) * 0.5
                if bullet_type == 0:
                    glColor4f(0.0, 1.0, 1.0, alpha)
                elif bullet_type == 1:
                    glColor4f(1.0, 0.5, 0.0, alpha)
                elif bullet_type == 2:
                    glColor4f(1.0, 0.0, 1.0, alpha)
                elif bullet_type == 3:
                    glColor4f(1.0, 0.0, 0.0, alpha)
                
                glPushMatrix()
                glTranslatef(trail_x, trail_y, trail_z)
                if bullet_type == 0:
                    glRotatef(90, 1, 0, 0)
                    gluCylinder(gluNewQuadric(), 1, 1, 10, 6, 1)
                else:
                    glutSolidSphere(2, 8, 8)
                glPopMatrix()
            
            glDisable(GL_BLEND)
        
        glPushMatrix()
        glTranslatef(bullet.x, bullet.y, bullet.z)
        
        if bullet_type == 0:
            glColor3f(0.0, 1.0, 1.0)
            glRotatef(90, 1, 0, 0)
            gluCylinder(gluNewQuadric(), 2, 2, 20, 8, 1)
        elif bullet_type == 1:
            glColor3f(1.0, 0.5, 0.0)
            glutSolidSphere(4, 12, 12)
            glColor4f(1.0, 0.5, 0.0, 0.3)
            glutSolidSphere(8, 12, 12)
        elif bullet_type == 2:
            glColor3f(1.0, 0.0, 1.0)
            glutSolidSphere(3, 10, 10)
            glColor4f(1.0, 0.0, 1.0, 0.4)
            glutSolidSphere(6, 10, 10)
        elif bullet_type == 3:
            glColor3f(1.0, 0.0, 0.0)
            glRotatef(90, 1, 0, 0)
            glutSolidCone(gluNewQuadric(), 3, 12, 8, 1)
            glTranslatef(0, 0, -6)
            glColor3f(0.8, 0.8, 0.8)
            gluCylinder(gluNewQuadric(), 2, 2, 8, 8, 1)
        
        glPopMatrix()
    glPopMatrix()

def draw_reticle():
    if camera_mode == 1:
        center_x, center_y = 500, 400
        glColor3f(1.0, 1.0, 1.0)
        draw_text(center_x - 5, center_y, "|", font=GLUT_BITMAP_HELVETICA_18)
        draw_text(center_x, center_y - 5, "-", font=GLUT_BITMAP_HELVETICA_18)
        draw_text(center_x, center_y, "+", font=GLUT_BITMAP_HELVETICA_18)

def draw_player():
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_rotation_y, 0, 0, 1)

    if camera_mode == 0:
        glColor3f(0.0, 0.8, 0.2)
        gluCylinder(gluNewQuadric(), 20, 20, 40, 16, 16)
        glTranslatef(0, 0, 40)
        gluSphere(gluNewQuadric(), 20, 16, 16)

        glColor3f(1.0, 0.0, 0.0)
        glPushMatrix()
        glTranslatef(0, 20, 0)
        glutSolidCube(10)
        glPopMatrix()

    glPopMatrix()

def draw_shapes():
    glPushMatrix()
    glColor3f(1, 0, 0)
    glTranslatef(-300, -300, 30)
    glutSolidCube(60)
    glTranslatef(0, 200, 0)
    glColor3f(0, 1, 0)
    glutSolidCube(60)
    glColor3f(1, 1, 0)
    glTranslatef(300, 0, -100)
    gluCylinder(gluNewQuadric(), 40, 5, 150, 10, 10)
    glTranslatef(100, 0, 100)
    glRotatef(90, 0, 1, 0)
    gluCylinder(gluNewQuadric(), 40, 5, 150, 10, 10)
    glColor3f(0, 1, 1)
    glTranslatef(300, 0, 100)
    gluSphere(gluNewQuadric(), 80, 10, 10)
    glPopMatrix()

def draw_trigger_zones():
    glPushMatrix()
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    for name, trigger in trigger_zones.items():
        if not trigger['activated']:
            bounds = trigger['bounds']
            x_min, x_max, y_min, y_max, z_min, z_max = bounds
            glColor4f(0.0, 0.0, 1.0, 0.2)
            glBegin(GL_QUADS)
            glVertex3f(x_min, y_min, z_min)
            glVertex3f(x_max, y_min, z_min)
            glVertex3f(x_max, y_max, z_min)
            glVertex3f(x_min, y_max, z_min)
            glVertex3f(x_min, y_min, z_max)
            glVertex3f(x_max, y_min, z_max)
            glVertex3f(x_max, y_max, z_max)
            glVertex3f(x_min, y_max, z_max)
            glVertex3f(x_min, y_min, z_min)
            glVertex3f(x_min, y_max, z_min)
            glVertex3f(x_min, y_max, z_max)
            glVertex3f(x_min, y_min, z_max)
            glVertex3f(x_max, y_min, z_min)
            glVertex3f(x_max, y_max, z_min)
            glVertex3f(x_max, y_max, z_max)
            glVertex3f(x_max, y_min, z_max)
            glVertex3f(x_min, y_min, z_min)
            glVertex3f(x_max, y_min, z_min)
            glVertex3f(x_max, y_min, z_max)
            glVertex3f(x_min, y_min, z_max)
            glVertex3f(x_min, y_max, z_min)
            glVertex3f(x_max, y_max, z_min)
            glVertex3f(x_max, y_max, z_max)
            glVertex3f(x_min, y_max, z_max)
            glEnd()
    glDisable(GL_BLEND)
    glPopMatrix()

def keyboardListener(key, x, y):
    global move_forward, move_backward, strafe_left, strafe_right
    global player_rotation_y, camera_mode, god_mode_active, player_pos
    global checkpoint_data, infinite_ammo, ammo_count, bullet_type
    global freeze_enemies, game_over

    if game_over and key == b'r':
        reset_game()
        return

    if key == b'w':
        move_forward = True
    elif key == b's':
        move_backward = True
    elif key == b'a':
        strafe_left = True
    elif key == b'd':
        strafe_right = True
    elif key == b' ' or key == b'\x20':
        fire_weapon()
    elif key == b'f':
        fire_weapon()
    elif key == b'v':
        camera_mode = 1 - camera_mode
        print(f"Camera mode: {'First-person' if camera_mode == 1 else 'Third-person'}")
    elif key == b'c':
        god_mode_active = not god_mode_active
        print(f"God Mode: {'ON' if god_mode_active else 'OFF'}")
    elif key == b'k':
        infinite_ammo = not infinite_ammo
        if infinite_ammo:
            ammo_count = max_ammo
        print(f"Infinite Ammo: {'ON' if infinite_ammo else 'OFF'}")
    elif key == b'm':
        freeze_enemies = not freeze_enemies
        print(f"Freeze Enemies: {'ON' if freeze_enemies else 'OFF'}")
    elif key == b'b':
        bullet_type = (bullet_type + 1) % 4
        bullet_types = ["Laser", "Energy Ball", "Plasma Bolt", "Missile"]
        print(f"Bullet Type: {bullet_types[bullet_type]}")
    elif key == b'p':
        checkpoint_data['player_pos'] = list(player_pos)
        checkpoint_data['player_rotation_y'] = player_rotation_y
        checkpoint_data['camera_mode'] = camera_mode
        print(f"Checkpoint saved at: {player_pos}")
    elif key == b'r':
        respawn_at_checkpoint()

def keyboardUpListener(key, x, y):
    global move_forward, move_backward, strafe_left, strafe_right
    if key == b'w':
        move_forward = False
    elif key == b's':
        move_backward = False
    elif key == b'a':
        strafe_left = False
    elif key == b'd':
        strafe_right = False

def specialKeyListener(key, x, y):
    global player_rotation_y
    if key == GLUT_KEY_LEFT:
        player_rotation_y += player_yaw_speed
    elif key == GLUT_KEY_RIGHT:
        player_rotation_y -= player_yaw_speed
    player_rotation_y %= 360

def mouseListener(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_weapon()

def fire_weapon():
    global bullets, ammo_count, last_shot_time, infinite_ammo
    
    current_time = time.time()
    
    if current_time - last_shot_time < weapon_fire_rate:
        return
    
    if not infinite_ammo and ammo_count <= 0:
        print("Out of ammo!")
        return
    
    angle_rad = math.radians(player_rotation_y)
    direction_x = math.sin(angle_rad)
    direction_y = math.cos(angle_rad)
    direction_z = 0.0
    
    if camera_mode == 0:
        bullet_x = player_pos[0] + direction_x * 30
        bullet_y = player_pos[1] + direction_y * 30
        bullet_z = player_pos[2] + 30
    else:
        bullet_x = player_pos[0] + direction_x * 50
        bullet_y = player_pos[1] + direction_y * 50
        bullet_z = player_pos[2] + 40
    
    new_bullet = Bullet(bullet_x, bullet_y, bullet_z, direction_x, direction_y, direction_z)
    bullets.append(new_bullet)
    
    if not infinite_ammo:
        ammo_count -= 1
    last_shot_time = current_time
    
    print(f"Fired! Ammo: {ammo_count}")

def update_bullets(delta_time):
    global bullets, enemies, score, score_effects
    
    bullets_to_remove = []
    for bullet in bullets:
        if not bullet.update(delta_time):
            bullets_to_remove.append(bullet)
    
    for bullet in bullets_to_remove:
        bullets.remove(bullet)
    
    for bullet in bullets:
        for enemy in enemies:
            distance = math.sqrt((bullet.x - enemy.x)**2 + (bullet.y - enemy.y)**2 + (bullet.z - enemy.z)**2)
            if distance < enemy.size / 2 + 5:
                if enemy.take_damage():
                    enemies.remove(enemy)
                    score += 100
                    score_effects.append(ScoreEffect(500, 400, 100))
                    print(f"Enemy killed! Score: {score}")
                bullets_to_remove.append(bullet)
                break
    
    for bullet in bullets_to_remove:
        if bullet in bullets:
            bullets.remove(bullet)

def spawn_enemy():
    global enemies
    
    side = random.randint(0, 3)
    if side == 0:
        x = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        y = GRID_LENGTH
    elif side == 1:
        x = random.uniform(-GRID_LENGTH, GRID_LENGTH)
        y = -GRID_LENGTH
    elif side == 2:
        x = -GRID_LENGTH
        y = random.uniform(-GRID_LENGTH, GRID_LENGTH)
    else:
        x = GRID_LENGTH
        y = random.uniform(-GRID_LENGTH, GRID_LENGTH)
    
    z = 30
    enemy_type = random.choice(["static", "charger"])
    new_enemy = Enemy(x, y, z, enemy_type)
    enemies.append(new_enemy)

def update_enemies(delta_time):
    global enemy_spawn_timer, game_health, game_lives, game_over
    
    if not freeze_enemies:
        enemy_spawn_timer += delta_time
        if enemy_spawn_timer >= enemy_spawn_rate:
            spawn_enemy()
            enemy_spawn_timer = 0.0
    
    for enemy in enemies[:]:
        enemy.update(delta_time)
        
        if not god_mode_active and not freeze_enemies:
            distance = math.sqrt((player_pos[0] - enemy.x)**2 + (player_pos[1] - enemy.y)**2)
            if distance < enemy.size / 2 + 20:
                apply_damage(10)
                print(f"Hit by enemy! Health: {game_health}")

def update_score_effects():
    global score_effects
    
    effects_to_remove = []
    for effect in score_effects:
        if not effect.update():
            effects_to_remove.append(effect)
    
    for effect in effects_to_remove:
        score_effects.remove(effect)

def apply_damage(amount):
    global game_health, game_lives, game_over
    
    if god_mode_active:
        return
    
    game_health -= amount
    if game_health <= 0:
        game_lives -= 1
        game_health = 100
        if game_lives <= 0:
            game_over = True
            print("GAME OVER!")
        else:
            respawn_at_checkpoint()
            print(f"Lives remaining: {game_lives}")

def respawn_at_checkpoint():
    global player_pos, player_rotation_y, camera_mode
    player_pos = list(checkpoint_data['player_pos'])
    player_rotation_y = checkpoint_data['player_rotation_y']
    camera_mode = checkpoint_data['camera_mode']
    print(f"Respawned at checkpoint: {player_pos}")

def reset_game():
    global player_pos, player_rotation_y, camera_mode, enemies, bullets
    global score, game_health, game_lives, game_over, ammo_count, infinite_ammo
    global god_mode_active, freeze_enemies, trigger_zones
    
    player_pos = [0.0, 0.0, 50.0]
    player_rotation_y = 0.0
    camera_mode = 0
    enemies = []
    bullets = []
    score = 0
    game_health = 100
    game_lives = 3
    game_over = False
    ammo_count = max_ammo
    infinite_ammo = False
    god_mode_active = False
    freeze_enemies = False
    
    for trigger in trigger_zones.values():
        trigger['activated'] = False
    
    print("Game reset!")

def update_player_movement():
    global player_pos, player_rotation_y

    angle_rad = math.radians(player_rotation_y)
    forward_x = math.sin(angle_rad)
    forward_y = math.cos(angle_rad)
    right_x = math.cos(angle_rad)
    right_y = -math.sin(angle_rad)

    dx, dy = 0, 0
    if move_forward:
        dx += forward_x * player_speed
        dy += forward_y * player_speed
    if move_backward:
        dx -= forward_x * player_speed
        dy -= forward_y * player_speed
    if strafe_left:
        dx -= right_x * player_speed
        dy -= right_y * player_speed
    if strafe_right:
        dx += right_x * player_speed
        dy += right_y * player_speed

    new_pos_x = player_pos[0] + dx
    new_pos_y = player_pos[1] + dy

    player_radius = 20

    if new_pos_x - player_radius < -GRID_LENGTH:
        new_pos_x = -GRID_LENGTH + player_radius
    elif new_pos_x + player_radius > GRID_LENGTH:
        new_pos_x = GRID_LENGTH - player_radius

    if new_pos_y - player_radius < -GRID_LENGTH:
        new_pos_y = -GRID_LENGTH + player_radius
    elif new_pos_y + player_radius > GRID_LENGTH:
        new_pos_y = GRID_LENGTH - player_radius

    player_pos[0] = new_pos_x
    player_pos[1] = new_pos_y

def check_triggers():
    global trigger_zones
    px, py, pz = player_pos
    for name, trigger in trigger_zones.items():
        if not trigger['activated']:
            x_min, x_max, y_min, y_max, z_min, z_max = trigger['bounds']
            if (x_min <= px <= x_max and
                    y_min <= py <= y_max and
                    z_min <= pz <= z_max):
                trigger['activated'] = True
                print(f"TRIGGER ACTIVATED: {trigger['message']}")

def setupCamera():
    global fovY
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    current_fovY = fovY
    if camera_mode == 1:
        current_fovY = 70

    window_width = 1000
    window_height = 800
    aspect_ratio = window_width / window_height

    gluPerspective(current_fovY, aspect_ratio, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    player_x, player_y, player_z = player_pos

    if camera_mode == 0:
        angle_rad = math.radians(player_rotation_y)
        cam_x = player_x + (-third_person_offset[1] * math.sin(angle_rad)) + (
                    third_person_offset[0] * math.cos(angle_rad))
        cam_y = player_y + (-third_person_offset[1] * math.cos(angle_rad)) - (
                    third_person_offset[0] * math.sin(angle_rad))
        cam_z = player_z + third_person_offset[2]

        gluLookAt(cam_x, cam_y, cam_z,
                  player_x, player_y, player_z + 30,
                  0, 0, 1)

    else:
        cam_x, cam_y, cam_z = player_x, player_y, player_z + 40
        target_distance = 100.0
        look_at_x = cam_x + target_distance * math.sin(math.radians(player_rotation_y))
        look_at_y = cam_y + target_distance * math.cos(math.radians(player_rotation_y))
        look_at_z = cam_z

        gluLookAt(cam_x, cam_y, cam_z,
                  look_at_x, look_at_y, look_at_z,
                  0, 0, 1)

def idle():
    global last_frame_time
    
    current_time = time.time()
    if not hasattr(idle, 'last_frame_time'):
        idle.last_frame_time = current_time
    delta_time = current_time - idle.last_frame_time
    idle.last_frame_time = current_time
    
    if not game_over:
        update_player_movement()
        check_triggers()
        update_bullets(delta_time)
        update_enemies(delta_time)
        update_score_effects()

    glutPostRedisplay()

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    viewport_width = glutGet(GLUT_WINDOW_WIDTH)
    viewport_height = glutGet(GLUT_WINDOW_HEIGHT)
    glViewport(0, 0, viewport_width, viewport_height)

    setupCamera()

    # ground
    glBegin(GL_QUADS)
    glColor3f(1, 1, 1)
    glVertex3f(-GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(0, GRID_LENGTH, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(-GRID_LENGTH, 0, 0)
    glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(0, -GRID_LENGTH, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(GRID_LENGTH, 0, 0)
    glColor3f(0.7, 0.5, 0.95)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0)
    glVertex3f(-GRID_LENGTH, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, -GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, GRID_LENGTH, 0)
    glVertex3f(GRID_LENGTH, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, GRID_LENGTH, 0)
    glEnd()

    draw_player()
    draw_shapes()
    draw_trigger_zones()
    draw_bullets()
    
    for enemy in enemies:
        enemy.draw()

    
    draw_text(10, 770, f"Player Pos: X={player_pos[0]:.1f}, Y={player_pos[1]:.1f}, Z={player_pos[2]:.1f}")
    draw_text(10, 750, f"Player Rot: {player_rotation_y:.1f} deg")
    draw_text(10, 730, f"Camera Mode: {'First-person' if camera_mode == 1 else 'Third-person'}")
    
    ammo_text = f"Ammo: {ammo_count}/{max_ammo}"
    if infinite_ammo:
        ammo_text += " (INFINITE)"
    draw_text(10, 710, ammo_text, color=(1.0, 1.0, 0.0))
    
    draw_text(10, 690, f"Score: {score}", color=(0.0, 1.0, 0.0))
    draw_text(10, 670, f"Health: {game_health}", color=(1.0, 0.0, 0.0))
    draw_text(10, 650, f"Lives: {game_lives}", color=(1.0, 0.0, 0.0))
    draw_text(10, 630, f"Enemies: {len(enemies)}", color=(1.0, 0.0, 0.0))
    draw_text(10, 610, f"Bullets: {len(bullets)}", color=(1.0, 1.0, 0.0))
    
    bullet_types = ["Laser", "Energy Ball", "Plasma Bolt", "Missile"]
    draw_text(10, 590, f"Bullet Type: {bullet_types[bullet_type]}", color=(0.5, 0.5, 1.0))

    if god_mode_active:
        draw_text(850, 770, "GOD MODE ON!", font=GLUT_BITMAP_HELVETICA_18, color=(1, 0, 0))

    if infinite_ammo:
        draw_text(850, 750, "INFINITE AMMO!", font=GLUT_BITMAP_HELVETICA_18, color=(0, 1, 0))
    
    if freeze_enemies:
        draw_text(850, 730, "FREEZE ENEMIES!", font=GLUT_BITMAP_HELVETICA_18, color=(0, 0, 1))

    for name, trigger in trigger_zones.items():
        if trigger['activated']:
            draw_text(10, 570, f"Trigger '{name}' Activated: {trigger['message']}", color=(0, 1, 0))

    draw_reticle()
    
    for effect in score_effects:
        effect.draw()
    
    if game_over:
        draw_text(400, 400, "GAME OVER - Press R to restart", font=GLUT_BITMAP_HELVETICA_18, color=(1, 0, 0))

    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(0, 0)
    wind = glutCreateWindow(b"Ruins Assault - Complete 3D Arcade Shooter")

    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)

    print("=== RUINS ASSAULT - COMPLETE GAME ===")
    print("Controls:")
    print("WASD - Move")
    print("Arrow Keys - Aim")
    print("Spacebar/F/Mouse - Shoot")
    print("V - Toggle camera mode")
    print("B - Cycle bullet types")
    print("C - God Mode")
    print("K - Infinite Ammo")
    print("M - Freeze Enemies")
    print("P - Set checkpoint")
    print("R - Respawn/Reset game")
    print("================================")

    glutMainLoop()

if __name__ == "__main__":
    main()
