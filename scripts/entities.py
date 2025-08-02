import math
import random

import pygame

from scripts.particle import Particle
from scripts.spark import Spark

class PhysicsEntity:
    def __init__(self, game, e_type, pos, size):
        self.game = game
        self.type = e_type
        self.pos = list(pos)
        self.size = size
        self.velocity = [0, 0]
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        
        self.action = ''
        self.anim_offset = (-3, -3)
        self.flip = False

        self.set_action('idle')
        
        self.last_movement = [0, 0]
    
    def rect(self):
        return pygame.Rect(self.pos[0], self.pos[1], self.size[0], self.size[1])
    
    def set_action(self, action):
        if action != self.action:
            self.action = action
            self.animation = self.game.assets[self.type + '/' + self.action].copy()
        
    def update(self, tilemap, movement=(0, 0)):
        self.collisions = {'up': False, 'down': False, 'right': False, 'left': False}
        
        frame_movement = (movement[0] + self.velocity[0], movement[1] + self.velocity[1])
        
        self.pos[0] += frame_movement[0]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[0] > 0:
                    entity_rect.right = rect.left
                    self.collisions['right'] = True
                if frame_movement[0] < 0:
                    entity_rect.left = rect.right
                    self.collisions['left'] = True
                self.pos[0] = entity_rect.x
        
        self.pos[1] += frame_movement[1]
        entity_rect = self.rect()
        for rect in tilemap.physics_rects_around(self.pos):
            if entity_rect.colliderect(rect):
                if frame_movement[1] > 0:
                    entity_rect.bottom = rect.top
                    self.collisions['down'] = True
                if frame_movement[1] < 0:
                    entity_rect.top = rect.bottom
                    self.collisions['up'] = True
                self.pos[1] = entity_rect.y
                
        if movement[0] > 0:
            self.flip = False
        if movement[0] < 0:
            self.flip = True
            
        self.last_movement = movement
        
        self.velocity[1] = min(5, self.velocity[1] + 0.1)
        
        if self.collisions['down'] or self.collisions['up']:
            self.velocity[1] = 0
            
        self.animation.update()
        
    def render(self, surf, offset=(0, 0)):
        surf.blit(pygame.transform.flip(self.animation.img(), self.flip, False), (self.pos[0] - offset[0] + self.anim_offset[0], self.pos[1] - offset[1] + self.anim_offset[1]))

class Friend(PhysicsEntity):
    def __init__(self, game, pos, size, Dialogue, name='friend',):
        super().__init__(game, 'friend', pos, size)
        self.talk_num = -1
        self.text = Dialogue["dialogueTree"][name]
        self.exclaim = ['WOAH', 'TOO CLOSE', 'STOP THAT']
        self.dialogue_ID = 'None'
        self.current_dialogue = ''
        self.name = name

    def woah(self):
        exclaim = random.randint(0,2)
        return self.exclaim[exclaim]
    def apply_flag_changes(self, choice_data):
        #"""Apply flag changes from a dialogue choice to the player's flags"""
        
        # Handle Melody_Song_flags_changes
        if "flags_changes" in choice_data:
            # Load current player data (you might want to load this from a file)
            # For now, we'll assume the game has access to player flags
            if not hasattr(self.game, 'player_flags'):
                self.game.player_flags = {"flags": {}}
            
            for flag in choice_data["flags_changes"]:
                self.game.player_flags["flags"][flag] = True
                print(f"Added flag: {flag}")

    def talk(self,num):

        if self.dialogue_ID == 'None':
            self.dialogue_ID = 'start'
        elif (isinstance(self.current_dialogue.get('choices'), list) and 0 <= num < len(self.current_dialogue['choices'])):
            # Get the chosen option
            chosen_choice = self.current_dialogue['choices'][num]
            
            # Apply any flag changes from this choice
            self.apply_flag_changes(chosen_choice)
            
            # Move to the next dialogue node
            if chosen_choice['nextNode']:
                self.dialogue_ID = chosen_choice['nextNode']
            
            if 'end of level' in chosen_choice:
                self.game.endLevel()

            

        # Also apply any flag changes from the current dialogue node itself
        if "flags_changes" in self.current_dialogue:
            choice_data = {"flags_changes": self.current_dialogue["flags_changes"]}
            self.apply_flag_changes(choice_data)

        if "end of level" in self.current_dialogue:
            self.game.endLevel()

        if "menu" in self.current_dialogue:
                self.game.openShop()
        self.current_dialogue = self.text[self.dialogue_ID]
        responses = ''

        if len(self.current_dialogue['choices']) !=0:
            i=1
            for text in self.current_dialogue['choices']:
                responses += '['+ str(i) +']'+text["text"] +'\n'
                i+=1

        return self.current_dialogue["speaker"] + ":" + self.current_dialogue["text"] + "\n\n" + responses
    
    def update(self, tilemap, movement=(0, 0)):
        super().update(tilemap, movement=movement)

        if abs(self.game.player.dashing) >= 50 and self.rect().colliderect(self.game.player.rect()):
                return True

class Enemy(PhysicsEntity):
    def __init__(self, game, type, pos, size):
        self.type = type
        super().__init__(game, str(self.type), pos, size)
        self.flip = not self.flip
        self.walking = 0
        
    def update(self, tilemap, movement=(0, 0)):
        if self.walking:
            movement = self.handle_movement(tilemap, movement)
            self.handle_attack()
        elif self.should_start_walking():
            self.start_walking()
        
        super().update(tilemap, movement=movement)
        self.update_animation(movement)
        return self.handle_collision_with_player()
    
    def handle_movement(self, tilemap, movement):
        foot_y = self.pos[1] + self.size[1]
        side_x = self.rect().centerx + (-self.size[0] // 2 if self.flip else self.size[0] // 2)
        
        if tilemap.solid_check((side_x, foot_y + 2)):
            if (self.collisions['right'] or self.collisions['left']):
                self.flip = not self.flip
            else:
                movement = (movement[0] - 0.5 if self.flip else 0.5, movement[1])
        else:
            self.flip = not self.flip
            
        self.walking = max(0, self.walking - 1)
        return movement
    
    def handle_attack(self):
        if self.type == 'enemy' and not self.walking:
            dis = (self.game.player.pos[0] - self.pos[0], self.game.player.pos[1] - self.pos[1])
            if (abs(dis[1]) < 16):
                self.shoot(dis)
    
    def shoot(self, dis):
        if (self.flip and dis[0] < 0):
            self.shoot_projectile(-7, -1.5, math.pi)
        if (not self.flip and dis[0] > 0):
            self.shoot_projectile(7, 1.5, 0)
    
    def shoot_projectile(self, x_offset, velocity, angle):
        self.game.sfx['shoot'].play()
        self.game.projectiles.append([[self.rect().centerx + x_offset, self.rect().centery], velocity, 0])
        for i in range(4):
            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5 + angle, 2 + random.random()))
    
    def should_start_walking(self):
        return random.random() < 0.01
    
    def start_walking(self):
        self.walking = random.randint(30, 120)
    
    def update_animation(self, movement):
        if movement[0] != 0:
            self.set_action('run')
        else:
            self.set_action('idle')
    
    def handle_collision_with_player(self):
        if abs(self.game.player.dashing) >= 50:
            if self.rect().colliderect(self.game.player.rect()):
                self.create_collision_effects()
                return True
        return False
    
    def create_collision_effects(self):
        self.game.screenshake = max(16, self.game.screenshake)
        self.game.sfx['hit'].play()
        for i in range(30):
            angle = random.random() * math.pi * 2
            speed = random.random() * 5
            self.game.sparks.append(Spark(self.rect().center, angle, 2 + random.random()))
            self.game.particles.append(Particle(self.game, 'particle', self.rect().center, 
                velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], 
                frame=random.randint(0, 7)))
        self.game.sparks.append(Spark(self.rect().center, 0, 5 + random.random()))
        self.game.sparks.append(Spark(self.rect().center, math.pi, 5 + random.random()))

class Judge(Enemy):
    def __init__(self, game, pos, size):
        super().__init__(game, 'judge', pos, size)
        self.patrol_distance = 100
        # Calculate proper animation cycle length
        self.run_anim_length = len(game.assets['judge/run'].images) * game.assets['judge/run'].img_duration
        self.idle_anim_length = len(game.assets['judge/idle'].images) * game.assets['judge/idle'].img_duration
        self.movement_speed = 0.7
        self.initial_flip = True
        
        # State management
        self.state = 'intro'  # 'intro', 'idle', 'running', 'gavel_and_idle'
        self.state_timer = 0
        self.run_cycles_remaining = 0
        
        # Gavel effect
        self.gavel_effect_pos = None
        self.gavel_effect_timer = 0
        
        # Set initial animation to intro
        self.set_action('intro')

    def update(self, tilemap, movement=(0, 0)):
        if self.state == 'intro':
            return self.handle_intro_state()
        elif self.state == 'idle':
            return self.handle_idle_state(tilemap, movement)
        elif self.state == 'running':
            return self.handle_running_state(tilemap, movement)
        elif self.state == 'gavel_and_idle':
            return self.handle_gavel_and_idle_state()
            
        return False

    def handle_intro_state(self):
        # Make sure judge faces player during intro
        self.flip = self.game.player.pos[0] < self.pos[0]
        
        # Update animation
        self.animation.update()
        
        # Check if intro animation is complete
        if self.animation.img() == self.game.assets['judge/intro'].images[-1]:
            self.state = 'idle'
            self.state_timer = self.idle_anim_length
            self.set_action('idle')
        
        return False

    def handle_idle_state(self, tilemap, movement):
        # Update the animation
        self.animation.update()
        
        self.state_timer -= 1
        
        # Wait for one full idle animation to complete
        if self.state_timer <= 0:
            # Calculate distance to player
            player_dist_x = self.game.player.pos[0] - self.pos[0]
            player_dist_y = self.game.player.pos[1] - self.pos[1]
            distance = (player_dist_x ** 2 + player_dist_y ** 2) ** 0.5
            tile_distance = distance / self.game.tilemap.tile_size
            
            if tile_distance < 4:
                # Run 1-3 cycles
                self.run_cycles_remaining = random.randint(1, 3)
                self.start_running()
            else:
                # 50% chance to run, 50% chance to gavel + idle
                if random.random() < 0.5:
                    self.run_cycles_remaining = random.randint(1, 3)
                    self.start_running()
                else:
                    self.start_gavel_and_idle()
        
        return False

    def handle_running_state(self, tilemap, movement):
        # Handle movement
        if self.walking:
            movement = self.handle_movement(tilemap, movement)
        
        # Update parent class
        super().update(tilemap, movement=movement)
        
        # Check if current run cycle is complete
        if not self.walking:
            self.run_cycles_remaining -= 1
            if self.run_cycles_remaining > 0:
                # Start next run cycle
                self.walking = self.run_anim_length
            else:
                # All run cycles complete, go back to idle
                self.state = 'idle'
                self.state_timer = self.idle_anim_length
                self.set_action('idle')
        
        return self.handle_collision_with_player()

    def handle_gavel_and_idle_state(self):
        # Update the idle animation
        self.animation.update()
        
        # Update gavel effect position
        if self.gavel_effect_pos:
            # Move gavel down 1 pixel per frame
            new_x = self.gavel_effect_pos[0]
            new_y = self.gavel_effect_pos[1] + 1
            self.gavel_effect_pos = (new_x, new_y)
            
            # Check if gavel has moved past judge's y coordinate
            if new_y > self.pos[1]+16:
                self.gavel_effect_pos = None
                self.gavel_effect_timer = 0
            else:
                # Check collision with player
                self.check_gavel_collision()
                # Keep gavel animation looping by incrementing timer
                self.gavel_effect_timer += 1
        
        self.state_timer -= 1
        
        # Wait for idle animation to complete
        if self.state_timer <= 0:
            # Reset gavel effect
            self.gavel_effect_pos = None
            self.gavel_effect_timer = 0
            # Go back to idle state for next cycle
            self.state = 'idle'
            self.state_timer = self.idle_anim_length
            self.set_action('idle')
        
        return False

    def start_running(self):
        self.state = 'running'
        self.walking = self.run_anim_length
        # Set direction toward player
        self.flip = self.game.player.pos[0] < self.pos[0]
        self.initial_flip = self.flip
        self.set_action('run')

    def start_gavel_and_idle(self):
        self.state = 'gavel_and_idle'
        self.state_timer = self.idle_anim_length
        
        # Create gavel effect 5 tiles above player's current position
        player_center_x = self.game.player.rect().centerx
        player_center_y = self.game.player.rect().centery
        gavel_y = player_center_y - (7 * self.game.tilemap.tile_size)
        
        self.gavel_effect_pos = (player_center_x, gavel_y)
        self.gavel_effect_timer = len(self.game.assets['judge/gavel'].images) * self.game.assets['judge/gavel'].img_duration
        
        # Judge continues idle animation while gavel effect plays above player
        self.flip = self.game.player.pos[0] < self.pos[0]  # Face player
        self.set_action('idle')

    def check_gavel_collision(self):
        """Check if the falling gavel collides with the player"""
        if self.gavel_effect_pos:
            # Get current gavel image for collision detection
            total_frames = len(self.game.assets['judge/gavel'].images)
            frame_duration = self.game.assets['judge/gavel'].img_duration
            frame_index = (self.gavel_effect_timer // frame_duration) % total_frames
            gavel_img = self.game.assets['judge/gavel'].images[frame_index]
            
            # Create gavel rect
            gavel_rect = pygame.Rect(
                self.gavel_effect_pos[0] - gavel_img.get_width() // 2,
                self.gavel_effect_pos[1] - gavel_img.get_height() // 2,
                gavel_img.get_width(),
                gavel_img.get_height()
            )
            
            # Check collision with player
            if gavel_rect.colliderect(self.game.player.rect()):
                # Kill player
                self.game.dead += 1
                self.game.sfx['hit'].play()
                self.game.screenshake = max(16, self.game.screenshake)
                
                # Create death effects
                for i in range(30):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 5
                    self.game.sparks.append(Spark(self.game.player.rect().center, angle, 2 + random.random()))
                    self.game.particles.append(Particle(self.game, 'particle', self.game.player.rect().center, 
                        velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], 
                        frame=random.randint(0, 7)))
                
                # Remove gavel effect after hit
                self.gavel_effect_pos = None
                self.gavel_effect_timer = 0

    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset=offset)
        # Render the gavel effect above the player if active
        if self.gavel_effect_pos:
            # Calculate which frame of gavel animation to show (looping)
            total_frames = len(self.game.assets['judge/gavel'].images)
            frame_duration = self.game.assets['judge/gavel'].img_duration
            frame_index = (self.gavel_effect_timer // frame_duration) % total_frames
            
            gavel_img = self.game.assets['judge/gavel'].images[frame_index]
            render_x = self.gavel_effect_pos[0] - offset[0] - gavel_img.get_width() // 2
            render_y = self.gavel_effect_pos[1] - offset[1] - gavel_img.get_height() // 2
            
            surf.blit(gavel_img, (render_x, render_y))

    def handle_movement(self, tilemap, movement):
        # Use the stored initial direction instead of updating based on player position
        self.flip = self.initial_flip

        foot_y = self.pos[1] + self.size[1]
        side_x = self.rect().centerx + (-self.size[0] // 2 if self.flip else self.size[0] // 2)
        
        if tilemap.solid_check((side_x, foot_y + 2)):
            if (self.collisions['right'] or self.collisions['left']):
                # When hitting a wall, reverse direction and store it
                self.flip = not self.flip
                self.initial_flip = self.flip
            else:
                # Use same speed - set directly, don't add to existing movement
                movement = (-self.movement_speed if self.flip else self.movement_speed, movement[1])
        else:
            # When reaching a ledge, reverse direction and store it
            self.flip = not self.flip
            self.initial_flip = self.flip
            
        self.walking = max(0, self.walking - 1)
        return movement

    def handle_collision_with_player(self):
        # Check if we're in the attack frame of run animation by checking current image
        current_img = self.animation.img()
        is_attack_frame = (self.action == 'run' and 
                         current_img in [self.game.assets['judge/run'].images[5],
                                         self.game.assets['judge/run'].images[6], 
                                       self.game.assets['judge/run'].images[7],
                                       self.game.assets['judge/run'].images[8],
                                       self.game.assets['judge/run'].images[9],
                                       self.game.assets['judge/run'].images[10]])

        if is_attack_frame and self.rect().colliderect(self.game.player.rect()):
            self.game.dead += 1
            self.game.sfx['hit'].play()
            self.game.screenshake = max(16, self.game.screenshake)
            for i in range(30):
                angle = random.random() * math.pi * 2
                speed = random.random() * 5
                self.game.sparks.append(Spark(self.game.player.rect().center, angle, 2 + random.random()))
                self.game.particles.append(Particle(self.game, 'particle', self.game.player.rect().center, 
                    velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], 
                    frame=random.randint(0, 7)))

        return super().handle_collision_with_player()
    

class Money(PhysicsEntity):
    def __init__(self, game, pos, value = 1, size=(16, 16)):
        super().__init__(game, 'money', pos, size)
        self.set_action('idle')  # Use your money animation
        self.value = value

    def update(self, tilemap, movement=(0, 0)):
        super().update(tilemap, movement=(0, 0))  # No movement
        # Check collision with player
        if self.rect().colliderect(self.game.player.rect()):
            # Add money to player, play sound, etc.
            self.game.player_state["money"] += self.value*self.game.player_state["upgrades"]["moneyLevel/moneyFrequency/moneyValue"]
            return True  # Signal to remove this entity
        return False
    
class Player(PhysicsEntity):
    def __init__(self, game, pos, size, screen_size):
        super().__init__(game, 'player', pos, size)
        self.set_action('idle')
        self.air_time = 0
        self.max_jumps = 2
        self.wall_slide = False
        self.dashing = 0
        self.jumps = self.max_jumps

        self.screen_size = screen_size
        self.interacting = False
        self.selecting = 0
        self.casting = False
    
    def update(self, tilemap, movement=(0, 0)):
        super().update(tilemap, movement=movement)
        old_velocity = self.velocity.copy()
        self.air_time += 1
        
        #kills you if you are falling for 2 seconds
        # if self.air_time > 120:
        #     if not self.game.dead:
        #         self.game.screenshake = max(16, self.game.screenshake)
        #     self.game.dead += 1
        
        if self.collisions['down']:
            self.air_time = 0
            self.jumps = self.max_jumps
            
        self.wall_slide = False
        if (self.collisions['right'] or self.collisions['left']) and self.air_time > 4:
            self.wall_slide = True
            self.velocity[1] = min(self.velocity[1], 0.5)
            if self.collisions['right']:
                self.flip = False
            else:
                self.flip = True
            self.set_action('wall_slide')

        if not self.wall_slide:
            if self.air_time > 4:
                self.set_action('jump')
            elif movement[0] != 0:
                self.set_action('run')
            else:
                self.set_action('idle')
        
        if abs(self.dashing) in {60, 50}:
            for i in range(20):
                angle = random.random() * math.pi * 2
                speed = random.random() * 0.5 + 0.5
                pvelocity = [math.cos(angle) * speed, math.sin(angle) * speed]
                self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=pvelocity, frame=random.randint(0, 7)))


        if self.dashing > 0:
            self.dashing = max(0, self.dashing - 1)
        if self.dashing < 0:
            self.dashing = min(0, self.dashing + 1)
        if abs(self.dashing) > 50:
            self.velocity[0] = abs(self.dashing) / self.dashing * 8
            if abs(self.dashing) == 51:
                self.velocity[0] *= 0.1
            pvelocity = [abs(self.dashing) / self.dashing * random.random() * 3, 0]
            self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=pvelocity, frame=random.randint(0, 7)))
        
        if self.velocity[0] > 0:
            self.velocity[0] = max(self.velocity[0] - 0.1, 0)
        else:
            self.velocity[0] = min(self.velocity[0] + 0.1, 0)
    
    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset=offset)
        if self.casting:
            print("casting")
            
            
    def closestFriend(self, surf, offset=(0, 0), max_distance=25):
        closest = None
        closest_dist = float('inf')
        player_rect = self.rect()
        for friend in self.game.friends:
            dist = math.hypot(
                player_rect.centerx - friend.rect().centerx,
                player_rect.centery - friend.rect().centery
            )
            if dist < closest_dist and dist <= max_distance:
                closest = friend
                closest_dist = dist
        if closest:
            icon_anim = self.game.assets['friend/closest_friend']
            if hasattr(icon_anim, 'update'):
                icon_anim.update()
                icon = icon_anim.img()
            else:
                icon = icon_anim
            friend_rect = closest.rect()
            icon_x = friend_rect.centerx - offset[0] - icon.get_width() // 2
            icon_y = friend_rect.top - offset[1] - icon.get_height()-4  # 4px above head
            surf.blit(icon, (icon_x, icon_y))
        return closest


    def jump(self,value,sensitivity = 0.2):
        if value <=1:
            if self.wall_slide:

                if self.flip and self.last_movement[0] < 0:
                    self.velocity[0] = 3.5
                elif not self.flip and self.last_movement[0] > 0:
                    self.velocity[0] = -3.5

                self.air_time = 0
                #self.jumps = max(0, self.jumps - 1)
                self.velocity[1] = -2.5
                self.game.sfx['jump'].play()

                return True
                    
            elif self.jumps:
                self.velocity[1] = -3
                self.jumps -= 1
                self.air_time = 0
                self.game.sfx['jump'].play()
                return True
        return False
    
    def dash(self,value,sensitivity = 0.2):
        if value<=1:
            if not self.dashing:
                self.game.sfx['dash'].play()
                if self.flip:
                    self.dashing = -60
                else:
                    self.dashing = 60

    def startCasting(self,value,sensitivity = 0.2):
        was_casting = self.casting
        if value<=1:
            self.casting = value > sensitivity
        else:
            self.casting=False
        if self.casting and not was_casting:
            self.restartCasting()
            
    
    def restartCasting(self):
        pass
        #self.game.assets['music/clefs'].frame = 0
        
        
    

    def moveHorizontal(self,value,sensitivity = 0.2):
        if (-1<=value<=1):
            self.game.movement[0] = value < -sensitivity
            self.game.movement[1] = value > sensitivity
        elif value ==-2:
            self.game.movement[0]=False
        elif value==2:
            self.game.movement[1]=False


    def moveVirtical(self,value,sensitivity = 0.2):#up=down down=up
        if (-2<value<2):
            if value>sensitivity:
                print("crouch")
            else:
                print("uncrouch")
            if value<-sensitivity:
                self.jump(value)
        else:
            print("uncrouch")

    def scroll(self, value, sensitivity=0.2):
        friend = self.game.closestFriend
        if friend:
            if "choices" in friend.current_dialogue and len(friend.current_dialogue["choices"]) > 0:
                if (-1<=value<=1):
                    self.selecting = (self.selecting + value) % len(friend.current_dialogue["choices"])
                    print(self.selecting)
    
    def interact(self, value, sensitivity=0.2):
        if value<0:
            pass
        elif value==0:
            value= self.selecting
        else:
            value= value-1 #using number keys
        friend = self.game.closestFriend
        if friend:
            self.game.current_dialogue = friend.talk(value)
            self.selecting=0

    def pause(self,value,sensitivity = 0.2):
        if value<=1:
            self.game.running = not self.game.running