# imports
import pygame, sys, random

# constants
# eg. SCREEN_WIDTH = 800

# Functions
def circles_collide(pos_a, r_a, pos_b, r_b):
    # Circle-circle collision using squared distance
    return pos_a.distance_squared_to(pos_b) <= (r_a +r_b) ** 2

class Asteroid:
    # Simple size tiers
    SIZE = {
        "big" : 40,
        "medium" : 26,
        "small" : 16
    }

    def __init__(self, pos, vel, size_name="big"):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.size_name = size_name
        self.radius = self.SIZE[size_name]

        # Optional: small spin for visuals
        self.angle = random.uniform(0 ,360)
        self.spin = random.uniform(-90, 90) # degrees per second
        
        # Jagged polygon outline
        self.local_points = self._make_jagged_points()
    
    def _make_jagged_points(self):
        points = []
        vertex_count = random.randint(9 ,14)

        for i in range(vertex_count):
            ang = (360 / vertex_count) * i
            r = self.radius * random.uniform(0.65, 1.15)
            points.append(pygame.Vector2(r, 0).rotate(ang))
        
        return points

    def update(self, dt, screen_size):
        self.pos += self.vel * dt
        self.angle = (self.angle + self.spin * dt) % 360

        w, h = screen_size
        if self.pos.x < 0:
            self.pos.x += w
        elif self.pos.x >= w:
            self.pos.x -= w

        if self.pos.y < 0:
            self.pos.y += h
        elif self.pos.y >= h:
            self.pos.y -= h

    def draw(self, surface):
        world_points = []
        for p in self.local_points:
            wp = p.rotate(self.angle) + self.pos
            world_points.append((int(wp.x), int(wp.y)))

        pygame.draw.polygon(surface, (160, 160, 170), world_points, width=2)
        
    def get_collision_circle(self):
        return self.pos, float(self.radius)
    
    def split(self):
        '''
        Returns a list of new Asteroid objects (children).
        big -> 2 medium
        medium -> 2 small
        small -> []
        '''
        if self.size_name == "small":
            return []
        
        next_size = "medium" if self.size_name == "big" else "small"

        children = []
        for _ in range(2):
            #Give each child a new direction/speed "kick"
            direction = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
            speed = random.uniform(120, 220) if next_size == "small" else random.uniform(90, 170)

            # Children inherits some of the parent's velocity
            child_vel = self.vel * 0.4 + direction * speed
            children.append(Asteroid(self.pos, child_vel, size_name=next_size))

        return children

class Bullet:
    def __init__(self, pos, vel, lifetime=1.2):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.lifetime = lifetime
        self.radius = 3

    def update(self, dt, screen_size):
        self.pos += self.vel * dt
        self.lifetime -= dt

        w, h = screen_size
        if self.pos.x < 0:
            self.pos.x += w
        elif self.pos.x >= w:
            self.pos.x -= w

        if self.pos.y < 0:
            self.pos.y += h
        elif self.pos.y >= h:
            self.pos.y -= h
        
        return self.lifetime > 0
    
    def draw(self, surface):
        pygame.draw.circle(surface, (252, 251, 157),
                           (int(self.pos.x), int(self.pos.y)), self.radius)
        
    def get_collision_circle(self):
        return self.pos, float(self.radius)
        

class Player:
    def __init__(self, pos):
        # Physics
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 0)

        # Ship orientation (degrees). 0 = pointing right
        self.angle = -90.0 # start pointing up

        # Tuning 
        self.turn_speed = 360.0 # degrees per second
        self.thrust_accel = 520.0 # pixels per second^2
        self.max_speed = 420.0 # clamp velocity magnitude 
        self.damping = 0.995 # slight drift reduction per frame (think of it as the lower the no, the air you walk through becomes water)

        # Rendering / collision
        self.radius = 16 # pixels (your hitbox)

        # Shooting 
        self.fire_cooldown = 0.06
        self._fire_timer = 0.0
        self.bullet_speed = 650.0 # pixels per second
        self.bullet_spawn_offset = self.radius + 4

        # Ultimate ability
        self.ultimate_charge = 0.0
        self.ultimate_max_charge = 100.0
        self.ultimate_duration = 0.0
        self.ultimate_active = False
        self.ultimate_cooldown = 10.0  # seconds
        self.ultimate_timer = 0.0

    def update(self, dt, keys, screen_size):
        self._fire_timer = max(0.0, self._fire_timer - dt)
        
        # Update ultimate timers
        if self.ultimate_active:
            self.ultimate_duration -= dt
            if self.ultimate_duration <= 0:
                self.ultimate_active = False
                self.ultimate_timer = self.ultimate_cooldown
        else:
            self.ultimate_timer = max(0.0, self.ultimate_timer - dt)
            
            # Charge ultimate by moving
            if self.vel.length() > 10:
                self.ultimate_charge = min(self.ultimate_max_charge, 
                                          self.ultimate_charge + dt * 15)

        # Rotation
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle -= self.turn_speed * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle += self.turn_speed * dt

        # Thrust (acceleration in facing direction)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            forward = pygame.Vector2(1, 0).rotate(self.angle)
            self.vel += forward * self.thrust_accel * dt

        # Clamp speed
        if self.vel.length() > self.max_speed:
            self.vel.scale_to_length(self.max_speed)

        # Move
        self.pos += self.vel * dt

        #Mild damping to keep things controllable
        self.vel *= self.damping

        # Screen wrap
        w, h = screen_size
        if self.pos.x < 0:
            self.pos.x += w
        elif self.pos.x >= w:
            self.pos.x -= w

        if self.pos.y < 0:
            self.pos.y += h
        elif self.pos.y >= h:
            self.pos.y -= h
    
    def try_fire(self):
        if self._fire_timer > 0.0:
            return None
        
        forward = pygame.Vector2(1, 0).rotate(self.angle)
        spawn_pos = self.pos + forward * self.bullet_spawn_offset
        bullet_vel = self.vel + forward * self.bullet_speed

        self._fire_timer = self.fire_cooldown
        return Bullet(spawn_pos, bullet_vel)

    def try_ultimate(self):
        """Try to activate ultimate ability"""
        if self.ultimate_timer > 0 or self.ultimate_active:
            return None
        
        if self.ultimate_charge >= self.ultimate_max_charge:
            self.ultimate_active = True
            self.ultimate_duration = 3.0  # Ultimate lasts 3 seconds
            self.ultimate_charge = 0.0
            return True
        return False
    
    def fire_ultimate_bullets(self):
        """Fire bullets in all directions"""
        bullets = []
        if self.ultimate_active:
            # Number of bullets depends on player's radius
            num_bullets = 24  # Shoot in all directions
            
            for i in range(num_bullets):
                angle = (360 / num_bullets) * i
                direction = pygame.Vector2(1, 0).rotate(angle)
                
                # Spawn from edge of player
                spawn_pos = self.pos + direction * (self.radius + 4)
                
                # Add player velocity to bullet
                bullet_vel = self.vel + direction * (self.bullet_speed * 1.2)
                
                # Create bullet with special color
                bullet = Bullet(spawn_pos, bullet_vel, 
                               lifetime=1.5)  # Purple for ultimate
                bullets.append(bullet)
            
        return bullets

    def _ship_points(self):
        '''
        Returns 3 points (traingle) in world space.
        We'll draw a simple triangle ship (very simple :D)
        '''
        # Define ship traingle in local space (pointing right), 
        # then rotate by angle and translate by pos
        tip = pygame.Vector2(self.radius, 0)
        left = pygame.Vector2(-self.radius * 0.8, self.radius * 0.6)
        right = pygame.Vector2(-self.radius * 0.8, -self.radius * 0.6)

        pts = [tip, left, right]
        return [p.rotate(self.angle) + self.pos for p in pts]
    
    def draw(self, surface):
        pygame.draw.polygon(surface, (220, 220, 240), 
                            self._ship_points(), width=2)
        
        # Optional: draw a tiny center dot (help sees pos)
        pygame.draw.circle(surface, (220, 220, 240),
                           (int(self.pos.x), int(self.pos.y)), 2)
        
    def get_collision_circle(self):
        return self.pos, float(self.radius)
    
    def respawn(self, pos):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(0, 0)
        self.angle = -90.0

class Game:
    # always start with self!
    def __init__(self, width=800, height=450, caption="Pygame OOP"):
        pygame.init()

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))

        self.clock = pygame.time.Clock()
        self.running = True

        self.font_big = pygame.font.Font(None, 56)
        self.font_small = pygame.font.Font(None, 38)

        # We'll use dt in later sessions for smoother movement
        self.dt = 0.0

        # center spawn ship
        self.player = Player((self.width / 2, self.height / 2))
        self.bullets = []

        self.asteroids = []
        self.target_asteroids = 5

        # simple game state 
        self.game_over = False

        # scoring + lives + waves
        self.score = 0
        self.lives = 3
        self.waves = 1

        # invulnerability after getting hit
        self.invuln_time = 2.0
        self.invuln_timer = 0.0

        # Ultimate bullet spawn timer
        self.ultimate_fire_timer = 0.0

        self.start_wave()

    def start_wave(self):
        # Spawn more asteroids each wave
        count = 4 + self.waves * 2 # wave 1 -> 6 asteroids, wave 2 -> 8, ...
        for _ in range(count):
            self.spawn_asteroid(size_name="big")

    def spawn_asteroid(self, size_name='big'):
        # Spawn along a random edge so we don't instantly collide in center
        w, h = self.width, self.height
        edge = random.choice(["top", "bottom", "left", "right"])

        if edge == "top":
            pos = pygame.Vector2(random.uniform(0, w), -5)
        elif edge == "bottom":
            pos = pygame.Vector2(random.uniform(0, w), h + 5)
        elif edge == "left":
            pos = pygame.Vector2(-5, random.uniform(0, h))
        else:
            pos = pygame.Vector2(w + 5, random.uniform(0, h))
            
        # Random drift velocity
        speed = random.uniform(60, 140) # speed in pixels per second
        direction = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
        vel = direction * speed

        self.asteroids.append(Asteroid(pos, vel, size_name=size_name))

    def reset(self):
        self.player = Player((self.width / 2, self.height / 2))
        self.bullets = []
        self.asteroids = []
        
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.waves = 1
        self.invuln_timer = 0.0
        
        self.start_wave()

    def award_points(self, size_name):
        # Smaller asteroids give more points
        if size_name == "big":
            self.score += 25
        elif size_name == "medium":
            self.score += 50
        else:
            self.score += 100
    
    def run(self):
        '''Main game loop'''
        while self.running:
            # dt in seconds (eg. 0.016 at ~60 FPS cus 1/60)
            # dt is also called frametime
            self.dt = self.clock.tick(60) / 1000.0

            # 1. Handle events (inputs)
            self.handle_events()
            self.update(self.dt)
            self.draw()

        self.quit()

    def handle_events(self):
        '''Handle all events (inputs)'''
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                if event.key == pygame.K_r and self.game_over:
                    self.reset()

                 # Activate ultimate with Q key
                if event.key == pygame.K_q and not self.game_over:
                    if self.player.try_ultimate():
                        # Ultimate activated
                        pass

    def update(self, dt):
        '''Update game state'''
        if self.game_over:
            return
        
        # Reduce invulnerability timer
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, (self.width, self.height))

        # NEW: hold SPACE tp fire continuously
        if keys[pygame.K_SPACE]:
            bullet = self.player.try_fire()
            if bullet is not None:
                self.bullets.append(bullet)

        # Handle ultimate firing
        if self.player.ultimate_active:
            self.ultimate_fire_timer += dt
            # Fire ultimate bullets every 0.1 seconds
            if self.ultimate_fire_timer >= 0.1:
                self.ultimate_fire_timer = 0
                ultimate_bullets = self.player.fire_ultimate_bullets()
                self.bullets.extend(ultimate_bullets)
        else:
            self.ultimate_fire_timer = 0.0

        alive = []
        for b in self.bullets:
            if b.update(dt, (self.width, self.height)):
                alive.append(b)
        self.bullets = alive

        # Update asteroids
        for a in self.asteroids:
            a.update(dt, (self.width, self.height))


        # # Keep asteroid count up (simple spawn system) -----> spawns asteroid everytime you destroy one
        # while len(self.asteroids) < self.target_asteroids:
        #     self.spawn_asteroid(size_name="big")

        # Collisions: bullets vs asteroids
        bullets_to_remove = set()
        asteroids_to_remove = set()
        new_asteroids = []

        for bi, b in enumerate(self.bullets):
            bpos, br = b.get_collision_circle()
            for ai, a in enumerate(self.asteroids):
                apos, ar = a.get_collision_circle()
                if circles_collide(bpos, br, apos, ar):
                   bullets_to_remove.add(bi)
                   asteroids_to_remove.add(ai)
                   
                   # Score + split
                   self.award_points(a.size_name)
                   new_asteroids.extend(a.split())
                   break
        
        if bullets_to_remove or asteroids_to_remove:
            self.bullets = [b for i, b in enumerate(self.bullets) if i not in bullets_to_remove]
            self.asteroids = [a for i, a in enumerate(self.asteroids) if i not in asteroids_to_remove]
            self.asteroids.extend(new_asteroids)

        # Collisions: players vs asteroids (lives + invuln)
        if self.invuln_timer <= 0.0:
            ppos, pr = self.player.get_collision_circle()
            for a in self.asteroids:
                apos, ar = a.get_collision_circle()
                if circles_collide(ppos, pr, apos, ar):
                    self.lives -= 1

                    if self.lives <= 0:
                        self.game_over = True
                    else:
                        # Respawns player in the center with invulnerability
                        self.player.respawn((self.width / 2, self.height / 2))
                        self.invuln_timer = self.invuln_time
                    break

        # Wave progression
        if not self.asteroids:
            self.waves += 1
            self.start_wave()

    def draw(self):
        '''Draw everything each frame'''
        self.screen.fill((157, 0, 255)) # Background colour

        for a in self.asteroids:
            a.draw(self.screen)

        for b in self.bullets:
            b.draw(self.screen)

        # Draw player with a blink effect if invulnerable
        if self.invuln_timer > 0.0:
            # Blink by skipping draw every few frames
            if int(self.invuln_timer * 10) % 2 == 0:
                self.player.draw(self.screen)
        else: 
            self.player.draw(self.screen)

        # HUD
        hud = self.font_small.render(
            "Score: {}  Lives:{}  Waves:{}".format(self.score, self.lives, self.waves),
            True, (220, 220, 220)
        )
        self.screen.blit(hud, (10, 10))

        # Draw ultimate charge bar
        bar_width = 200
        bar_height = 20
        bar_x = 10
        bar_y = 50
        
        # Background bar
        pygame.draw.rect(self.screen, (60, 60, 60), 
                        (bar_x, bar_y, bar_width, bar_height))
        
        # Charge bar
        charge_width = (self.player.ultimate_charge / self.player.ultimate_max_charge) * bar_width
        if self.player.ultimate_active:
            charge_color = (255, 100, 255)  # Purple when active
        elif self.player.ultimate_timer > 0:
            charge_color = (100, 100, 100)  # Gray when on cooldown
        else:
            charge_color = (100, 255, 100)  # Green when ready
            
        pygame.draw.rect(self.screen, charge_color,
                        (bar_x, bar_y, charge_width, bar_height))
        
        # Bar border
        pygame.draw.rect(self.screen, (220, 220, 220),
                        (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Ultimate text
        if self.player.ultimate_active:
            ult_text = self.font_small.render("ULTIMATE ACTIVE!", True, (255, 100, 255))
        elif self.player.ultimate_timer > 0:
            ult_text = self.font_small.render(f"Cooldown: {self.player.ultimate_timer:.1f}s", True, (220, 220, 220))
        elif self.player.ultimate_charge >= self.player.ultimate_max_charge:
            ult_text = self.font_small.render("ULTIMATE READY! (Press Q)", True, (100, 255, 100))
        else:
            ult_text = self.font_small.render("Ultimate charging...", True, (220, 220, 220))
            
        self.screen.blit(ult_text, (bar_x + bar_width + 20, bar_y))

        if self.game_over:
            text = self.font_big.render("GAME OVER", True, (240, 80, 80))
            hint = pygame.font.Font(None, 28).render("Press R to restart", True, (220, 220, 220))

            rect = text.get_rect(center=(self.width / 2, self.height / 2 - 20))
            rect2 = hint.get_rect(center=(self.width / 2, self.height / 2 + 40))

            # Create a rectangle box for the background box
            padding = 20
            box_rect = rect.inflate(padding * 2, padding * 2)

            # Draw filled rectangle (background box)
            pygame.draw.rect(self.screen, (40, 40, 40), box_rect)
            # draw border around box
            pygame.draw.rect(self.screen, (240, 80, 80), box_rect, 3)

            # Draw text on top
            self.screen.blit(text, rect)
            self.screen.blit(hint, rect2)

        pygame.display.flip()

    def quit(self):
        '''Clean shutdown'''
        pygame.quit()
        sys.exit()
    

# Main loop
def main():
    Game().run()

# Script entry point
if __name__ == "__main__":
    main()
