#https://www.youtube.com/watch?v=2gABYM5M0ww  for directions for making the executable  https://www.youtube.com/watch?v=jGg_1h0qzaM for AI
import os
import sys
import math
import random

import pygame
import json

from scripts.utils import load_image, load_images, Animation
from scripts.compose import Composition
from scripts.entities import PhysicsEntity, Player, Enemy, Friend
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark

class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption('Disasterpiece (one for sorrow)')
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

            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'player': load_image('entities/player.png'),
            'background': load_image('background.png'),
            'clouds': load_images('clouds'),
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),

            'friend/idle': Animation(load_images('entities/friend/idle'), img_dur=6),
            'friend/closest_friend': Animation(load_images('entities/friend/closest_friend'), img_dur=10),

            'player/lyla_idle': Animation(load_images('entities/player/lyla_idle'), img_dur=6),
            'player/lyla_run': Animation(load_images('entities/player/lyla_run'), img_dur=4),
            'player/lyla_jump': Animation(load_images('entities/player/lyla_jump'),img_dur=1,loop=False),
            'player/slide': Animation(load_images('entities/player/slide_old')),
            'player/lyla_wall_slide': Animation(load_images('entities/player/lyla_wall_slide')),
            'player/lyla_flying': Animation(load_images('entities/player/lyla_flying')),

            'player/melody_idle': Animation(load_images('entities/player/melody_idle'), img_dur=6),

            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png'),

            'music/clefs': Animation(load_images('music/clefs'), img_dur=20,loop=False),
            'music/key_signatures/flats': Animation(load_images('music/key_signatures/flats'), img_dur=10,loop=False),
            'music/key_signatures/sharps': Animation(load_images('music/key_signatures/sharps'), img_dur=10,loop=False),
            'music/notes/rests': Animation(load_images('music/notes/rests'), img_dur=10,loop=False),
            'music/notes/stem_down': Animation(load_images('music/notes/stem_down'), img_dur=10,loop=False),
            'music/notes/stem_up': Animation(load_images('music/notes/stem_up'), img_dur=10,loop=False),
            'music/time_signature': Animation(load_images('music/time_signature'), img_dur=10,loop=False),
            "music/staf": load_image('music/staf.png')
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
        self.player = Player(self, (50, 50), (28, 30),[self.info.current_w,self.info.current_h])

        self.measuresUnlocked = []
        self.clefsUnlocked = []
        self.keysignaturesUnlocked = []
        self.timeSignaturesUnlocked = []
        self.notesUnlocked = []
        self.compositions = {}

        self.tilemap = Tilemap(self, tile_size=16)
        
        self.level = 0
        self.load_level(self.level)
        
        self.screenshake = 0

    @property
    def team(self):
        return {
            'Melody_Team': self.player_state.get('Melody_Team', []),
            'Lyla_Team': self.player_state.get('Lyla_Team', [])
        }
    @property
    def player_flags(self):
        return {
            'Melody_Song_flags':self.player_state['Melody_Song_flags'],'Lyla_Silence_flags':self.player_state['Lyla_Silence_flags']
        } 

        
    def load_level(self, map_id):
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        self.sfx['ambience'].play(-1)
        pygame.mixer.pause()

        self.tilemap.load('data/maps/' + str(map_id) + '.json')
        
        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
            
        self.enemies = []
        self.friends = []

        f = open('data/story/'+ str(map_id)+'.json', 'r')
        Level_Dialogue = json.load(f)
        f.close

        f = open('data/story/Player.json', 'r')
        self.player_state = json.load(f)
        f.close()

        

        # self.compositions["Lyla"] = [Composition(self.assets,self.measuresUnlocked,self.clefsUnlocked,self.keysignaturesUnlocked,self.timeSignaturesUnlocked,self.notesUnlocked)]

        # self.compositions["Melody"] = [Composition(self.assets,self.measuresUnlocked,self.clefsUnlocked,self.keysignaturesUnlocked,self.timeSignaturesUnlocked,self.notesUnlocked)]

        #replaces each of the spawners with its character
        for spawner in self.tilemap.extract([('spawners', i) for i in range(len(os.listdir('data/images/tiles/spawners')))]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
            elif spawner['variant'] == 1:
                self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))
            elif spawner['variant'] == 2:
                self.friends.append(Friend(self,spawner['pos'],(28, 30),Level_Dialogue, 'Corwin'))
            elif spawner['variant'] == 3:
                self.friends.append(Friend(self,spawner['pos'],(28, 30), Level_Dialogue, 'Lyla'))
            
            
        self.projectiles = []
        self.particles = []
        self.sparks = []
        
        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -30

    def endLevel(self):

        f = open('data/story/Player.json', 'w')
        json.dump(self.player_state,f, indent=4)
        f.close()

        print("saved flags")
        transitioning = True
        while transitioning:
            self.transition += 1
            if self.transition > 30:
                self.level = min(self.level + 1, len(os.listdir('data/maps')) - 1)
                self.load_level(self.level)
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
                    self.level = min(self.level + 1, len(os.listdir('data/maps')) - 1)
                    self.load_level(self.level)
            if self.transition < 0:
                self.transition += 1
            
            if self.dead:
                self.dead += 1
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1)
                if self.dead > 40:
                    self.load_level(self.level)
            
            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))
            
            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))
            
            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll)
            
            self.tilemap.render(self.display, offset=render_scroll)
            
            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0, 0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.enemies.remove(enemy)
            
            for friend in self.friends.copy():
                kill = friend.update(self.tilemap, (0, 0))
                friend.render(self.display, offset=render_scroll)
                if kill:
                    print(friend.woah())
                    
            self.closestFriend = self.player.closestFriend(self.display, offset=render_scroll) #interact icon
            


            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

                # #RENDER_SCALE = 6
                # mpos = pygame.mouse.get_pos()
                # mpos = (mpos[0] *(320/self.info.current_w), mpos[1] *(240/self.info.current_h))
                # pygame.draw.line(self.display, (0, 255, 0), (self.player.pos[0]-self.scroll[0], self.player.pos[1]-self.scroll[1]), (mpos[0],mpos[1]), 2)
            
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
                    
            # display_mask = pygame.mask.from_surface(self.display)
            # display_sillhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
            # for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            #     self.display_2.blit(display_sillhouette, offset)
            
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
            self.draw_multiline_text(self.screen, self.current_dialogue, self.font, (0,0,0), 0, 0)

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
        tabs = ["Settings", "Inventory", "Team"]  # Removed "Compose" tab

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

    def handle_team_button_clicks(self, mx, my, sw, sh, y_start):
        """Handle clicks on up/down and compose buttons for Melody_Team and Lyla_Team"""
        row_height = 60
        button_width = 100
        button_height = 30
        button_spacing = 10
        compose_button_width = 80

        y_offset = y_start + 40
        for team_key in ["Melody_Team", "Lyla_Team"]:
            team_list = self.player_state.get(team_key, [])
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

                # Compose button clicks
                for c in range(3):
                    compose_rect = pygame.Rect(250 + c * (compose_button_width + 10), y_pos, compose_button_width, button_height)
                    if compose_rect.collidepoint(mx, my):
                        self.open_composition_editor(member, f"Compose {c+1}")
                        return

            y_offset += len(team_list) * row_height + 20
        
    def open_composition_editor(self, member_name, composition_type):
        """Open the composition editor for a specific team member and composition type"""
        # This is where you would implement opening your composition editor
        # For now, just print what would be opened
        print(f"Opening {composition_type} editor for {member_name}")
        
        # Example: You might call a method like:
        # self.composition_editor.open(member_name, composition_type)
        # or set a flag to switch to the composition editor state:
        # self.game_state = "composition_editor"
        # self.current_member = member_name
        # self.current_composition_type = composition_type

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
        
        # Example content - replace with your actual inventory system
        items = ["Potion", "Key", "Map", "Scroll"]
        for i, item in enumerate(items):
            item_text = self.font.render(f"• {item}", True, (200, 200, 200))
            self.screen.blit(item_text, (70, y_start + 40 + i * 30))

    def draw_team_tab(self, sw, sh, y_start, mx, my):
        """Draw the team tab content with rearrange and compose buttons for Melody_Team and Lyla_Team"""
        header = self.font.render("Team", True, (255, 255, 255))
        self.screen.blit(header, (50, y_start))

        teams = [
            ("Melody's Team", self.player_state.get("Melody_Team", [])),
            ("Lyla's Team", self.player_state.get("Lyla_Team", []))
        ]
        row_height = 60
        button_width = 100
        button_height = 30
        button_spacing = 10
        compose_button_width = 80

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

                # Draw Compose buttons
                for c in range(3):
                    compose_rect = pygame.Rect(250 + c * (compose_button_width + 10), y_pos, compose_button_width, button_height)
                    compose_color = (120, 120, 200) if compose_rect.collidepoint(mx, my) else (60, 60, 120)
                    pygame.draw.rect(self.screen, compose_color, compose_rect)
                    pygame.draw.rect(self.screen, (255, 255, 255), compose_rect, 2)
                    compose_text = self.font.render(f"Compose {c+1}", True, (255, 255, 255))
                    self.screen.blit(compose_text, compose_rect.move(5, 5))

            y_offset += len(team_list) * row_height + 20


    def addComposer(self):
        pass
    
Game().run()