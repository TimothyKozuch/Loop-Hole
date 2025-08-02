#https://www.youtube.com/watch?v=2gABYM5M0ww  for directions for making the executable  https://www.youtube.com/watch?v=jGg_1h0qzaM for AI
import os
import sys
import math
import random

import pygame
import json

from scripts.utils import load_image, load_images, load_image_with_black, load_images_with_black, Animation
from scripts.entities import PhysicsEntity, Player, Enemy, Friend, Judge
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark
from scripts.entities import Money

class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption('Loop-Hole')
        self.info = pygame.display.Info()
        self.screen = pygame.display.set_mode((self.info.current_w, self.info.current_h), pygame.RESIZABLE)
        self.display = pygame.Surface((320, 240), pygame.SRCALPHA)
        self.display_2 = pygame.Surface((320, 240))

        self.font = pygame.font.Font(None, 36)

        self.input_mode = "KEYBOARD"  # or "CONTROLLER"
        self.awaiting_rebind = None
        self.running = True

        self.closestFriend = None
        self.current_dialogue = ''
        

        self.clock = pygame.time.Clock()
        
        self.movement = [False, False]
        self.axis_states = {}  # Add this line


        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'wood': load_images('tiles/wood'),
            'concrete': load_images_with_black('tiles/concrete'),

            'buildings': load_images_with_black('tiles/buildings'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'player': load_image('entities/player.png'),
            'background': load_image('background.png'),
            'clouds': load_images('clouds'),
            
            'enemy/idle': Animation(load_images_with_black('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images_with_black('entities/enemy/run'), img_dur=4),

            'judge/intro': Animation(load_images_with_black('entities/judge/intro'), img_dur=4),
            'judge/idle': Animation(load_images_with_black('entities/judge/idle'), img_dur=15),
            'judge/run': Animation(load_images_with_black('entities/judge/run'), img_dur=10),

            'friend/idle': Animation(load_images_with_black('entities/friend/idle'), img_dur=6),
            'friend/closest_friend': Animation(load_images_with_black('entities/friend/closest_friend'), img_dur=10),

            'player/idle': Animation(load_images_with_black('entities/player/idle'), img_dur=6),
            'player/run': Animation(load_images_with_black('entities/player/run'), img_dur=4),
            'player/jump': Animation(load_images_with_black('entities/player/jump'),img_dur=1,loop=False),
            'player/slide': Animation(load_images_with_black('entities/player/slide')),
            'player/wall_slide': Animation(load_images_with_black('entities/player/wall_slide')),
            'money/idle': Animation(load_images_with_black('entities/money/idle'), img_dur=6),

            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/paper': Animation(load_images('particles/paper'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png'),
        }
        
        self.sfx = {
            'jump': pygame.mixer.Sound('data/sfx/jump.wav'),
            'dash': pygame.mixer.Sound('data/sfx/dash.wav'),
            'hit': pygame.mixer.Sound('data/sfx/hit.wav'),
            'shoot': pygame.mixer.Sound('data/sfx/shoot.wav'),
            'ambience': pygame.mixer.Sound('data/sfx/ambience.wav'),
        }
        
        self.sfx['ambience'].set_volume(0.2)
        self.sfx['shoot'].set_volume(0.4)
        self.sfx['hit'].set_volume(0.8)
        self.sfx['dash'].set_volume(0.3)
        self.sfx['jump'].set_volume(0.7)
        
        self.clouds = Clouds(self.assets['clouds'], count=16)
        #8,15
        self.player = Player(self, (50, 50), (16, 29),[self.info.current_w,self.info.current_h])

        self.tilemap = Tilemap(self, tile_size=16)
        
        self.load_level()
        
        self.screenshake = 0

    @property
    def team(self):
        return self.player_state.get('Team', [])
    @property
    def player_flags(self):
        return self.player_state['flags']
    @property
    def upgrades(self):
        return self.player_state.get('upgrades')
    @property
    def inventory(self):
        return self.player_state.get('inventory', [])
    @property
    def equipped(self):
        return self.player_state.get('equipped')
        
    def load_level(self):
        
        f = open('data/story/Player.json', 'r')
        self.player_state = json.load(f)
        f.close()
        
        f = open('data/story/'+ str(self.player_state["level"]) +'.json', 'r')
        Level_Dialogue = json.load(f)
        f.close
        
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        self.sfx['ambience'].play(-1)
        pygame.mixer.pause()

        self.tilemap.load('data/maps/' + str(self.player_state["level"]) + '.json')
        
        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
            
        self.enemies = []
        self.friends = []
        self.money = []
        self.shop_open = False

        #replaces each of the spawners with its character
        for spawner in self.tilemap.extract([('spawners', i) for i in range(len(os.listdir('data/images/tiles/spawners')))]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
                self.player_dialogue = Level_Dialogue['dialogueTree']['Lawyer']['start']
            elif spawner['variant'] == 1:
                self.enemies.append(Enemy(self, 'enemy', spawner['pos'], (16, 29)))
            elif spawner['variant'] == 2:
                self.friends.append(Friend(self,spawner['pos'],(16, 29), Level_Dialogue, 'Accountant'))
            elif spawner['variant'] == 3:
                self.enemies.append(Judge(self, spawner['pos'], (16, 60)))
            
        self.projectiles = []
        self.particles = []
        self.sparks = []
        
        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -30

    def endLevel(self):
        
        transitioning = True
        while transitioning:
            self.transition += 1
            if self.transition > 30:
                self.player_state["level"] = min(self.player_state["level"] + 1, len(os.listdir('data/maps')) - 1)

                f = open('data/story/Player.json', 'w')
                json.dump(self.player_state,f, indent=4)
                f.close()
                print("saved")

                self.load_level()
                transitioning = False

    def draw_multiline_text(self,screen, text, font, color, x, y, line_spacing=5):
        lines = text.split('\n')
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, color)
            screen.blit(text_surface, (x, y + i * (font.get_height() + line_spacing)))

    def run(self):
        self.running = True
        pygame.mixer.unpause()
        
        while self.running:
            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0))
            
            self.screenshake = max(0, self.screenshake - 1)

            joysticks = {}
            
            if not len(self.enemies):
                self.transition += 1
                if self.transition > 30:
                    self.endLevel()
            if self.transition < 0:
                self.transition += 1
            
            if self.dead:
                self.dead += 1
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1)
                if self.dead > 40:
                    self.load_level()
            
            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))
            
            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            #paper effect
            if random.random() * 49999 < self.player.rect().width * self.player.rect().height:
                    pos = (self.player.rect().x + random.random() * self.player.rect().width, self.player.rect().y + random.random() * self.player.rect().height)
                    self.particles.append(Particle(self, 'paper', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll)
            
            self.tilemap.render(self.display, offset=render_scroll)
            
            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0, 0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.lootMoney(enemy.rect().center)
                    self.enemies.remove(enemy)
            
            for friend in self.friends.copy():
                kill = friend.update(self.tilemap, (0, 0))
                friend.render(self.display, offset=render_scroll)
                if kill:
                    print(friend.woah())

            for money in self.money.copy():
                kill = money.update(self.tilemap, (0, 0))
                money.render(self.display, offset=render_scroll)
                if kill:
                    self.money.remove(money)
                    
            self.closestFriend = self.player.closestFriend(self.display, offset=render_scroll) #interact icon
            
            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            # [[x, y], direction, timer]
            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile']
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    for i in range(4):
                        self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                elif projectile[2] > 360:
                    self.projectiles.remove(projectile)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().collidepoint(projectile[0]):
                        self.projectiles.remove(projectile)
                        self.dead += 1
                        self.sfx['hit'].play()
                        self.screenshake = max(16, self.screenshake)
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))
                        
            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)
                    
            display_mask = pygame.mask.from_surface(self.display)
            display_sillhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_sillhouette, offset)
            
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)
            
            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    # This event will be generated when the program starts for every
                    # joystick, filling up the list without needing to create them manually.
                    joy = pygame.joystick.Joystick(event.device_index)
                    joysticks[joy.get_instance_id()] = joy

                if event.type == pygame.JOYDEVICEREMOVED:
                    del joysticks[event.instance_id]

                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                #keyboard and mouse
                elif event.type in (pygame.KEYUP, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    self.input_mode = "KEYBOARD"
                    
                    # Get the key/button name
                    if event.type in (pygame.KEYUP, pygame.KEYDOWN):
                        key_name = pygame.key.name(event.key)
                    elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                        key_name = "mouse_" + str(event.button)
                    
                    keyBind = self.player_state["controls"]["KEYBOARD"]
                    if key_name in keyBind:
                        keyBinding = keyBind[key_name]
                        value = keyBinding["value"]
                        
                        # Handle key/button release
                        if event.type in (pygame.KEYUP, pygame.MOUSEBUTTONUP):
                            if keyBinding["action"] == "interact":
                                value = -1
                            else:
                                value = value * 2
                        
                        # Execute action safely
                        if hasattr(self.player, keyBinding["action"]):
                            if "sensitivity" in keyBinding:
                                getattr(self.player, keyBinding["action"])(value, keyBinding["sensitivity"])
                            else:
                                getattr(self.player, keyBinding["action"])(value)
                
                #controller support
                elif event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
                    self.input_mode = "CONTROLLER"
                    keyBind = self.player_state["controls"]["CONTROLLER"]
                    
                    # Map event types to button name formats
                    if event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYBUTTONUP:
                        button_name = f"BUTTONDOWN_{event.button}"
                    elif event.type == pygame.JOYHATMOTION:
                        button_name = f"HATMOTION_{event.value}"
                    elif event.type == pygame.JOYAXISMOTION:
                        button_name = f"AXISMOTION_{event.axis}"
                    
                    if button_name in keyBind:
                        keyBinding = keyBind[button_name]
                        value = keyBinding.get("value", getattr(event, "value", None))
                        
                        # Handle button release
                        if event.type == pygame.JOYBUTTONUP:
                            value = -1 if keyBinding["action"] == "interact" else value * 2
                        
                        # Execute action
                        if hasattr(self.player, keyBinding["action"]):
                            if "sensitivity" in keyBinding:
                                getattr(self.player, keyBinding["action"])(value, keyBinding["sensitivity"])
                            else:
                                getattr(self.player, keyBinding["action"])(value)



                    # if event.axis == 5 and event.value > 0.5:
                    #     print("Right trigger pressed!")
                    
                    
            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), (30 - abs(self.transition)) * 8)
                transition_surf.set_colorkey((255, 255, 255))
                self.display.blit(transition_surf, (0, 0))
                
            self.display_2.blit(self.display, (0, 0))
            
            screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), screenshake_offset)

            # Draw the dialogue text
            speaker = self.player_dialogue.get('speaker', 'Player')
            text = self.player_dialogue.get('text', '...')
            self.screen.blit(self.font.render(speaker + ": " + text , True, (0, 0, 0)), (0, 0))
            self.draw_multiline_text(self.screen, self.current_dialogue, self.font, (0,0,0), 0, 0)

            self.render_hud()

            pygame.display.update()
            self.clock.tick(60)

        self.pause()
  
  
    def pause(self):
        paused = True
        clock = pygame.time.Clock()
        button_height = 40
        col_spacing = 30
        y_start = 80  # Leave space for tabs
        selected_index = 0
        selected_tab = 0
        tabs = ["Settings", "Inventory", "Team"]  

        # Settings-specific variables
        key_formatters = {
            "BUTTONDOWN_": lambda x: f"Button {x.split('_')[1]}",
            "AXISMOTION_": lambda x: f"Axis {x.split('_')[1]}",
            "HATMOTION_": lambda x: f"Hat {x.split('_')[1]}",
            "mouse_": lambda x: f"Mouse {x.split('_')[1]}"
        }

        controller_event_map = {
            pygame.JOYBUTTONDOWN: lambda e: f"BUTTONDOWN_{e.button}",
            pygame.JOYAXISMOTION: lambda e: f"AXISMOTION_{e.axis}",
            pygame.JOYHATMOTION: lambda e: f"HATMOTION_{e.value}"
        }

        while paused:
            sw, sh = self.screen.get_size()
            button_width = sw // 4
            tab_width = sw // len(tabs)
            mx, my = pygame.mouse.get_pos()

            # --- Event Handling ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.awaiting_rebind:
                            self.awaiting_rebind = None
                        else:
                            paused = False
                    elif event.key == pygame.K_LEFT and not self.awaiting_rebind:
                        selected_tab = (selected_tab - 1) % len(tabs)
                        selected_index = 0  # Reset selection when changing tabs
                    elif event.key == pygame.K_RIGHT and not self.awaiting_rebind:
                        selected_tab = (selected_tab + 1) % len(tabs)
                        selected_index = 0  # Reset selection when changing tabs
                    
                    # Settings-specific keyboard handling
                    elif tabs[selected_tab] == "Settings":
                        if event.key == pygame.K_RETURN and not self.awaiting_rebind:
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            if keybind_list and selected_index < len(keybind_list):
                                self.awaiting_rebind = keybind_list[selected_index][0]
                        elif event.key == pygame.K_UP and not self.awaiting_rebind:
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            if keybind_list:
                                selected_index = (selected_index - 1) % len(keybind_list)
                        elif event.key == pygame.K_DOWN and not self.awaiting_rebind:
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            if keybind_list:
                                selected_index = (selected_index + 1) % len(keybind_list)
                        elif self.awaiting_rebind and self.input_mode == "KEYBOARD":
                            # Handle key rebinding
                            new_key = pygame.key.name(event.key)
                            keybinds = self.player_state["controls"][self.input_mode]
                            if new_key not in keybinds:
                                keybinds[new_key] = keybinds.pop(self.awaiting_rebind)
                                self.awaiting_rebind = None

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Tab click detection
                    for i, tab in enumerate(tabs):
                        tab_rect = pygame.Rect(i * tab_width, 0, tab_width, button_height)
                        if tab_rect.collidepoint(mx, my):
                            selected_tab = i
                            selected_index = 0  # Reset selection when changing tabs
                            break
                    
                    # Settings-specific mouse handling
                    if tabs[selected_tab] == "Settings":
                        if self.awaiting_rebind and self.input_mode == "KEYBOARD":
                            new_key = f"mouse_{event.button}"
                            keybinds = self.player_state["controls"][self.input_mode]
                            if new_key not in keybinds:
                                keybinds[new_key] = keybinds.pop(self.awaiting_rebind)
                                self.awaiting_rebind = None
                        else:
                            # Handle settings button clicks
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            
                            if keybind_list:
                                max_per_col = max(1, (sh - 2 * y_start) // (button_height + 10))
                                num_cols = (len(keybind_list) + max_per_col - 1) // max_per_col
                                total_width = num_cols * button_width + (num_cols - 1) * col_spacing
                                x_start = (sw - total_width) // 2
                                
                                x, y, col = x_start, y_start, 0
                                for idx, (key_name, bind) in enumerate(keybind_list):
                                    btn_rect = pygame.Rect(x, y, button_width, button_height)
                                    if btn_rect.collidepoint(mx, my):
                                        self.awaiting_rebind = key_name
                                        selected_index = idx
                                        break
                                    y += button_height + 10
                                    if (idx + 1) % max_per_col == 0:
                                        y = y_start
                                        col += 1
                                        x = x_start + col * (button_width + col_spacing)
                    
                    # Team tab composition button handling
                    elif tabs[selected_tab] == "Team":
                        self.handle_team_button_clicks(mx, my, sw, sh, y_start)

                # Controller handling
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 7:  # Back button
                        if self.awaiting_rebind:
                            self.awaiting_rebind = None
                        else:
                            paused = False
                    elif event.button == 0 and not self.awaiting_rebind:  # A button
                        if tabs[selected_tab] == "Settings":
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            if keybind_list and selected_index < len(keybind_list):
                                self.awaiting_rebind = keybind_list[selected_index][0]
                    elif event.button == 4 and not self.awaiting_rebind:  # Left shoulder
                        selected_tab = (selected_tab - 1) % len(tabs)
                        selected_index = 0
                    elif event.button == 5 and not self.awaiting_rebind:  # Right shoulder
                        selected_tab = (selected_tab + 1) % len(tabs)
                        selected_index = 0

                elif event.type == pygame.JOYHATMOTION and not self.awaiting_rebind:
                    if event.value == (0, 1):  # Up
                        if tabs[selected_tab] == "Settings":
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            if keybind_list:
                                selected_index = (selected_index - 1) % len(keybind_list)
                    elif event.value == (0, -1):  # Down
                        if tabs[selected_tab] == "Settings":
                            keybinds = self.player_state["controls"][self.input_mode]
                            keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
                            if keybind_list:
                                selected_index = (selected_index + 1) % len(keybind_list)
                    elif event.value == (-1, 0):  # Left
                        selected_tab = (selected_tab - 1) % len(tabs)
                        selected_index = 0
                    elif event.value == (1, 0):  # Right
                        selected_tab = (selected_tab + 1) % len(tabs)
                        selected_index = 0

                # Controller rebinding
                elif self.awaiting_rebind and self.input_mode == "CONTROLLER" and event.type in controller_event_map:
                    new_key = controller_event_map[event.type](event)
                    keybinds = self.player_state["controls"][self.input_mode]
                    if new_key not in keybinds:
                        keybinds[new_key] = keybinds.pop(self.awaiting_rebind)
                        self.awaiting_rebind = None

            # --- Drawing ---
            scaled = pygame.transform.scale(self.display, self.screen.get_size())
            self.screen.blit(scaled, (0, 0))
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            # Draw tabs
            for i, tab in enumerate(tabs):
                tab_rect = pygame.Rect(i * tab_width, 0, tab_width, button_height)
                color = (120, 120, 200) if i == selected_tab else (60, 60, 60)
                pygame.draw.rect(self.screen, color, tab_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), tab_rect, 2)
                text = self.font.render(tab, True, (255, 255, 255))
                text_rect = text.get_rect(center=tab_rect.center)
                self.screen.blit(text, text_rect)

            # Draw content based on selected tab
            if tabs[selected_tab] == "Settings":
                self.draw_settings_tab(sw, sh, y_start, button_width, button_height, col_spacing, selected_index, mx, my, key_formatters)
                                    
            elif tabs[selected_tab] == "Inventory":
                self.draw_inventory_tab(sw, sh, y_start)
                
            elif tabs[selected_tab] == "Team":
                self.draw_team_tab(sw, sh, y_start, mx, my)

            pygame.display.update()
            clock.tick(60)

        self.awaiting_rebind = None
        self.run()

    def handle_team_button_clicks(self, mx, my, sw, sh, y_start):
        """Handle clicks on up/down and other buttons"""
        row_height = 60
        button_width = 100
        button_height = 30
        button_spacing = 10
        other_button_width = 80

        y_offset = y_start + 40
        for team_key in ["Team"]:
            team_list = self.team
            y_offset += 30  # For team label
            for i, member in enumerate(team_list):
                y_pos = y_offset + i * row_height
                up_rect = pygame.Rect(sw - 2 * button_width - button_spacing - 50, y_pos, button_width, button_height)
                down_rect = pygame.Rect(sw - button_width - 50, y_pos, button_width, button_height)

                if up_rect.collidepoint(mx, my) and i > 0:
                    team_list[i], team_list[i-1] = team_list[i-1], team_list[i]
                    self.player_state[team_key] = team_list
                    return
                if down_rect.collidepoint(mx, my) and i < len(team_list) - 1:
                    team_list[i], team_list[i+1] = team_list[i+1], team_list[i]
                    self.player_state[team_key] = team_list
                    return

                # other button clicks
                for c in range(3):
                    other_rect = pygame.Rect(250 + c * (other_button_width + 10), y_pos, other_button_width, button_height)
                    if other_rect.collidepoint(mx, my):
                        self.other(member, f"other {c+1}")
                        return

            y_offset += len(team_list) * row_height + 20
        
    def other(self, member_name, other_type):
        """Open the other editor for a specific team member and other type"""
        # This is where you would implement opening your other editor
        # For now, just print what would be opened
        print(f"Opening {other_type} editor for {member_name}")

    def draw_settings_tab(self, sw, sh, y_start, button_width, button_height, col_spacing, 
                        selected_index, mx, my, key_formatters):
        """Draw the settings tab content"""
        keybinds = self.player_state["controls"][self.input_mode]
        keybind_list = sorted(keybinds.items(), key=lambda item: (item[1]["action"], item[0]))
        
        if not keybind_list:
            text = self.font.render("No keybinds found", True, (255, 255, 255))
            self.screen.blit(text, (50, y_start))
            return
        
        max_per_col = max(1, (sh - 2 * y_start) // (button_height + 10))
        num_cols = (len(keybind_list) + max_per_col - 1) // max_per_col
        total_width = num_cols * button_width + (num_cols - 1) * col_spacing
        x_start = (sw - total_width) // 2
        
        # Clamp selected index
        selected_index = max(0, min(selected_index, len(keybind_list) - 1))
        
        # Draw keybind buttons
        x, y, col = x_start, y_start, 0
        for idx, (key_name, bind) in enumerate(keybind_list):
            action = bind["action"]
            btn_rect = pygame.Rect(x, y, button_width, button_height)
            
            # Determine colors
            if self.awaiting_rebind == key_name:
                color, text_color = (200, 100, 100), (255, 255, 255)
            elif idx == selected_index:
                color, text_color = (100, 150, 100), (255, 255, 255)
            elif btn_rect.collidepoint(mx, my):
                color, text_color = (120, 120, 200), (255, 255, 0)
            else:
                color, text_color = (60, 60, 60), (255, 255, 255)
            
            pygame.draw.rect(self.screen, color, btn_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 2)
            
            # Format key name
            display_key = key_name.capitalize()
            for prefix, formatter in key_formatters.items():
                if key_name.startswith(prefix):
                    display_key = formatter(key_name)
                    break
            
            # Draw text with proper fitting
            text_str = f"{action.capitalize()}: {display_key}"
            text = self.font.render(text_str, True, text_color)
            
            # Truncate text if too long
            if text.get_width() > button_width - 10:
                text_str = text_str[:20] + "..."
                text = self.font.render(text_str, True, text_color)
            
            self.screen.blit(text, (btn_rect.x + 5, btn_rect.y + 10))
            
            y += button_height + 10
            if (idx + 1) % max_per_col == 0:
                y = y_start
                col += 1
                x = x_start + col * (button_width + col_spacing)
        
        # Draw instructions/prompts
        if self.awaiting_rebind:
            input_type = "button/axis/hat" if self.input_mode == "CONTROLLER" else "key or mouse button"
            display_key = self.awaiting_rebind.capitalize()
            for prefix, formatter in key_formatters.items():
                if self.awaiting_rebind.startswith(prefix):
                    display_key = formatter(self.awaiting_rebind)
                    break
            
            prompt = self.font.render(
                f"Press a {input_type} for '{display_key}'... (ESC to cancel)",
                True, (255, 255, 0)
            )
            self.screen.blit(prompt, (x_start, sh - 80))
        else:
            if self.input_mode == "CONTROLLER":
                instruction = "D-pad: navigate | A: select | LB/RB: switch tabs | Back: exit"
            else:
                instruction = "Arrows: navigate | Enter: select | Tab keys: switch tabs | ESC: exit"
            
            instruction_text = self.font.render(instruction, True, (200, 200, 200))
            self.screen.blit(instruction_text, (x_start, sh - 50))

    def draw_inventory_tab(self, sw, sh, y_start):
        """Draw the inventory tab content"""
        # Header
        header = self.font.render("Inventory", True, (255, 255, 255))
        self.screen.blit(header, (50, y_start))

        # Use the inventory property directly
        inventory_data = self.inventory
        y_offset = y_start + 40
        for collection_name, items in inventory_data.items():
            # Draw collection name
            collection_text = self.font.render(f"{collection_name}:", True, (180, 220, 255))
            self.screen.blit(collection_text, (70, y_offset))
            y_offset += 30
            # Draw each item in the collection
            if items:
                for item in items:
                    item_text = self.font.render(f"• {item}", True, (200, 200, 200))
                    self.screen.blit(item_text, (100, y_offset))
                    y_offset += 25
            else:
                empty_text = self.font.render("• (empty)", True, (120, 120, 120))
                self.screen.blit(empty_text, (100, y_offset))
                y_offset += 25
            y_offset += 10  # Space between collections

    def draw_team_tab(self, sw, sh, y_start, mx, my):
        """Draw the team tab content with rearrange and other buttons for Team"""
        header = self.font.render("Team", True, (255, 255, 255))
        self.screen.blit(header, (50, y_start))

        teams = [("Player Team", self.team)]
        row_height = 60
        button_width = 100
        button_height = 30
        button_spacing = 10
        other_button_width = 80

        y_offset = y_start + 40
        for team_label, team_list in teams:
            # Draw team label
            label_text = self.font.render(team_label, True, (180, 220, 255))
            self.screen.blit(label_text, (70, y_offset))
            y_offset += 30

            for i, member in enumerate(team_list):
                y_pos = y_offset + i * row_height

                # Draw member name
                member_text = self.font.render(f"• {member}", True, (200, 200, 200))
                self.screen.blit(member_text, (100, y_pos))

                # Draw up/down buttons
                up_rect = pygame.Rect(sw - 2 * button_width - button_spacing - 50, y_pos, button_width, button_height)
                down_rect = pygame.Rect(sw - button_width - 50, y_pos, button_width, button_height)

                up_color = (120, 180, 120) if up_rect.collidepoint(mx, my) else (80, 120, 80)
                down_color = (180, 120, 120) if down_rect.collidepoint(mx, my) else (120, 80, 80)

                pygame.draw.rect(self.screen, up_color, up_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), up_rect, 2)
                pygame.draw.rect(self.screen, down_color, down_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), down_rect, 2)

                up_text = self.font.render("Up", True, (255, 255, 255))
                down_text = self.font.render("Down", True, (255, 255, 255))
                self.screen.blit(up_text, up_rect.move(20, 5))
                self.screen.blit(down_text, down_rect.move(10, 5))

                # Draw other buttons
                for c in range(3):
                    other_rect = pygame.Rect(250 + c * (other_button_width + 10), y_pos, other_button_width, button_height)
                    other_color = (120, 120, 200) if other_rect.collidepoint(mx, my) else (60, 60, 120)
                    pygame.draw.rect(self.screen, other_color, other_rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), other_rect, 2)
                    other_text = self.font.render(f"other {c+1}", True, (255, 255, 255))
                    self.screen.blit(other_text, other_rect.move(5, 5))

            y_offset += len(team_list) * row_height + 20

    def addother(self):
        pass
    
    def openShop(self):
        self.shop_open = True
        self.shop_menu()
        self.shop_open = False

    def shop_menu(self):
        shop_running = True
        clock = pygame.time.Clock()
        sw, sh = self.screen.get_size()
        exit_btn_rect = pygame.Rect(sw // 2 - 80, sh - 120, 160, 50)

        # Prepare inventory and upgrades
        inventory_data = self.inventory  # dict of collections
        upgrades_data = self.upgrades    # dict of upgrades

        # Layout
        col_width = sw // 3
        col_spacing = 40
        y_start = 120
        button_height = 40

        while shop_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()
                    # Exit button
                    if exit_btn_rect.collidepoint(mx, my):
                        shop_running = False
                    # Inventory buttons
                    y_offset = y_start
                    for idx, (collection, items) in enumerate(inventory_data.items()):
                        x = col_spacing
                        for item_idx, item in enumerate(items):
                            btn_rect = pygame.Rect(x, y_offset, col_width - 2 * col_spacing, button_height)
                            if btn_rect.collidepoint(mx, my):
                                print(f"Clicked inventory item: {item} in {collection}")
                            y_offset += button_height + 10
                        y_offset += 20
                    # Upgrades buttons
                    y_offset = y_start
                    x = sw // 2 + col_spacing
                    for idx, (upgrade, value) in enumerate(upgrades_data.items()):
                        cost = 10 * (value + 1)  # Example cost formula
                        btn_rect = pygame.Rect(x, y_offset, col_width - 2 * col_spacing, button_height)
                        if btn_rect.collidepoint(mx, my):
                            if self.player_state["money"] >= cost:
                                upgrades_data[upgrade] += 1
                                self.player_state["money"] -= cost
                                print(f"Upgraded {upgrade} to level {upgrades_data[upgrade]}")
                            else:
                                print("Not enough money!")
                        y_offset += button_height + 10

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        shop_running = False

            # --- Drawing ---
            scaled = pygame.transform.scale(self.display, self.screen.get_size())
            self.screen.blit(scaled, (0, 0))
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            # Money display (top right)
            money_img = self.assets['money/idle'].img()
            base_w, base_h = 320, 180
            scale_x = sw / base_w
            scale_y = sh / base_h
            scale = min(scale_x, scale_y)
            scaled_size = (int(money_img.get_width() * scale), int(money_img.get_height() * scale))
            money_img_scaled = pygame.transform.scale(money_img, scaled_size)
            img_x = sw - money_img_scaled.get_width() - 30
            img_y = 30
            self.screen.blit(money_img_scaled, (img_x, img_y))
            money_count = self.player_state["money"]
            money_text = self.font.render(str(money_count), True, (255, 255, 0))
            self.screen.blit(money_text, (img_x - money_text.get_width() - 10, img_y + money_img_scaled.get_height() // 2 - money_text.get_height() // 2))

            # Shop header
            shop_header = self.font.render("Shop", True, (255, 255, 0))
            self.screen.blit(shop_header, (sw // 2 - shop_header.get_width() // 2, 40))

            # Inventory column
            x = col_spacing
            y_offset = y_start
            inv_header = self.font.render("Inventory", True, (255, 255, 255))
            self.screen.blit(inv_header, (x, y_offset - 40))
            for collection, items in inventory_data.items():
                col_text = self.font.render(f"{collection}:", True, (180, 220, 255))
                self.screen.blit(col_text, (x, y_offset))
                y_offset += 30
                for item in items:
                    btn_rect = pygame.Rect(x, y_offset, col_width - 2 * col_spacing, button_height)
                    pygame.draw.rect(self.screen, (80, 120, 180), btn_rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 2)
                    item_text = self.font.render(str(item), True, (255, 255, 255))
                    self.screen.blit(item_text, (btn_rect.x + 10, btn_rect.y + 8))
                    y_offset += button_height + 10
                y_offset += 20

            # Upgrades column
            x = sw // 2 + col_spacing
            y_offset = y_start
            upg_header = self.font.render("Upgrades", True, (255, 255, 255))
            self.screen.blit(upg_header, (x, y_offset - 40))
            for upgrade, value in upgrades_data.items():
                cost = 10 * (value + 1)  # Example cost formula
                btn_rect = pygame.Rect(x, y_offset, col_width - 2 * col_spacing, button_height)
                pygame.draw.rect(self.screen, (120, 180, 120), btn_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 2)
                upg_text = self.font.render(f"{upgrade}: {value}", True, (255, 255, 255))
                self.screen.blit(upg_text, (btn_rect.x + 10, btn_rect.y + 8))
                # Draw cost on the right side of the button
                cost_text = self.font.render(f"Cost: {cost}", True, (255, 255, 0))
                self.screen.blit(cost_text, (btn_rect.right - cost_text.get_width() - 10, btn_rect.y + 8))
                y_offset += button_height + 10

            # Exit Shop button
            pygame.draw.rect(self.screen, (180, 60, 60), exit_btn_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), exit_btn_rect, 2)
            exit_text = self.font.render("Exit Shop", True, (255, 255, 255))
            self.screen.blit(exit_text, (exit_btn_rect.x + 20, exit_btn_rect.y + 10))

            pygame.display.update()
            clock.tick(60)

    def lootMoney(self, center, value=1):
        self.money.append(Money(self, center, value, size=(12, 6)))
    
    def render_hud(self):
        # Money HUD (top right)
        money_img = self.assets['money/idle'].img()  # Use your money animation's idle frame
        sw, sh = self.screen.get_size()
        # Calculate scale factor (assuming your base resolution is 320x180, adjust as needed)
        base_w, base_h = 320, 180
        scale_x = sw / base_w
        scale_y = sh / base_h
        scale = min(scale_x, scale_y)
        scaled_size = (int(money_img.get_width() * scale), int(money_img.get_height() * scale))
        money_img_scaled = pygame.transform.scale(money_img, scaled_size)
        img_x = sw - money_img_scaled.get_width() - 30
        img_y = 30
        self.screen.blit(money_img_scaled, (img_x, img_y))
        money_count = self.player_state["money"]
        money_text = self.font.render(str(money_count), True, (255, 255, 0))
        self.screen.blit(money_text, (img_x - money_text.get_width() - 10, img_y + money_img_scaled.get_height() // 2 - money_text.get_height() // 2))
        
Game().run()