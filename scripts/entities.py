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
        
        self.walking = 0
        
    def update(self, tilemap, movement=(0, 0)):
        if self.walking:
            foot_y = self.pos[1] + self.size[1]  # bottom of enemy
            side_x = self.rect().centerx + (-self.size[0] // 2 if self.flip else self.size[0] // 2)
            if tilemap.solid_check((side_x, foot_y + 2)):  # +2 to check just below the feet
                if (self.collisions['right'] or self.collisions['left']):
                    self.flip = not self.flip
                else:
                    movement = (movement[0] - 0.5 if self.flip else 0.5, movement[1])
            else:
                self.flip = not self.flip
            self.walking = max(0, self.walking - 1)
            if not self.walking:
                dis = (self.game.player.pos[0] - self.pos[0], self.game.player.pos[1] - self.pos[1])
                if (abs(dis[1]) < 16):
                    if (self.flip and dis[0] < 0):
                        self.game.sfx['shoot'].play()
                        self.game.projectiles.append([[self.rect().centerx - 7, self.rect().centery], -1.5, 0])
                        for i in range(4):
                            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5 + math.pi, 2 + random.random()))
                    if (not self.flip and dis[0] > 0):
                        self.game.sfx['shoot'].play()
                        self.game.projectiles.append([[self.rect().centerx + 7, self.rect().centery], 1.5, 0])
                        for i in range(4):
                            self.game.sparks.append(Spark(self.game.projectiles[-1][0], random.random() - 0.5, 2 + random.random()))

        elif random.random() < 0.01:
            self.walking = random.randint(30, 120)
        
        super().update(tilemap, movement=movement)
        
        if movement[0] != 0:
            self.set_action('run')
        else:
            self.set_action('idle')
            
        if abs(self.game.player.dashing) >= 50:
            if self.rect().colliderect(self.game.player.rect()):
                self.game.screenshake = max(16, self.game.screenshake)
                self.game.sfx['hit'].play()
                for i in range(30):
                    angle = random.random() * math.pi * 2
                    speed = random.random() * 5
                    self.game.sparks.append(Spark(self.rect().center, angle, 2 + random.random()))
                    self.game.particles.append(Particle(self.game, 'particle', self.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))
                self.game.sparks.append(Spark(self.rect().center, 0, 5 + random.random()))
                self.game.sparks.append(Spark(self.rect().center, math.pi, 5 + random.random()))
                return True
            
    def render(self, surf, offset=(0, 0)):
        super().render(surf, offset=offset)
        
        if self.flip:
            surf.blit(pygame.transform.flip(self.game.assets['gun'], True, False), (self.rect().centerx - 4 - self.game.assets['gun'].get_width() - offset[0], self.rect().centery - offset[1]))
        else:
            surf.blit(self.game.assets['gun'], (self.rect().centerx + 4 - offset[0], self.rect().centery - offset[1]))

class Judge(Enemy):
    def __init__(self, game, pos, size):
        super().__init__(game, 'judge', pos, size)

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