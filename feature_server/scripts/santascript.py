
from commands import add
from pyspades.contained import BlockAction, SetColor
from pyspades.constants import *
from pyspades.world import Grenade
from pyspades.common import Vertex3
from pyspades.server import orientation_data, grenade_packet
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from math import sin, cos
import random

SCORE_REQUIREMENT = 15
remaining_time = 8

def apply_script(protocol, connection, config):
   class SantaConnection(connection):
      def on_block_build_attempt(self, x, y, z):
         c1, c2, c3 = self.color
         if ((c1 - c2) > 50 and (c1 - c3)) > 50 and abs(c2 - c3) <20:
            self.send_chat('This block color is too close to the color of the santa-script presents.')
            return False
         return connection.on_block_build_attempt(self, x, y, z)
		 
      def on_line_build_attempt(self, points):
         c1, c2, c3 = self.color
         if ((c1 - c2) > 50 and (c1 - c3)) > 50 and abs(c2 - c3) <20:
            self.send_chat('This block color is too close to the color of the santa-script presents.')
            return False
         return connection.on_line_build_attempt(self, points)
      
      def spew_santa_grenades(self, x, y, z):
         santa_nade = False
         for i in xrange(0, 7):
            grenade_packet.value = 3 # fuse
            grenade_packet.player_id = 32
            grenade_packet.position = (x, y, z)
            pi = 3.14159265
            a = i * ((2 * pi) / 7)
            
            vel_x = sin(a) * 1.5
            vel_y = cos(a) * 1.5
            vel_z = 1.0
            
            grenade_packet.velocity = (vel_x, vel_y, vel_z)
            self.protocol.send_contained(grenade_packet)
            
            position = Vertex3(x, y, z)
            velocity = Vertex3(vel_x, vel_y, vel_z)
            
            santa_nade = self.protocol.world.create_object(Grenade, 3, 
               position, None, velocity, self.grenade_exploded)
            santa_nade = 'Santa'
      
      def spawn_santa_grenade_fountain(self, x, y, z):
         santa_nade = False
         grenade_packet.value = 3 # fuse
         grenade_packet.player_id = 32
         grenade_packet.position = (x, y, z)

         vel_x = random.random() * random.uniform(-1.5, 1.5) #random.randrange(-1, 2, 2)
         vel_y = random.random() * random.uniform(-2, 2)
         vel_z = -0.5
            
         grenade_packet.velocity = (vel_x, vel_y, vel_z)
         self.protocol.send_contained(grenade_packet)
            
         position = Vertex3(x, y, z)
         velocity = Vertex3(vel_x, vel_y, vel_z)
            
         santa_nade = self.protocol.world.create_object(Grenade, 3, 
            position, None, velocity, self.grenade_exploded)
         santa_nade = 'Santa'
            
      def grenade_fountain(self, x, y, z):
         for i in xrange(32):
            time = i * 0.25
            reactor.callLater(time, self.spawn_santa_grenade_fountain, 
                          x, y, z)
						  
      def invisibility(self):
         if self.name and self.invisible:
            self.invisible = False
            self.filter_visibility_data = False
            self.send_chat('You are no longer invisible.')

      def flight(self):
         if self.name and self.fly:
            self.fly = False
            self.send_chat('You are no longer flying.')

      def countdown_warning_fly(self):
         if self.name and self.fly and self.remaining_time > 0:
            self.send_chat('%d...' % self.remaining_time)
            self.remaining_time -= 1
            reactor.callLater(1, self.countdown_warning_fly)
         elif self.name and self.fly and self.remaining_time == 0:
            pass	

      def countdown_warning_inv(self):
         if self.name and self.invisible and self.remaining_time1 > 0:
            self.send_chat('%d...' % self.remaining_time1)
            self.remaining_time1 -= 1
            reactor.callLater(1, self.countdown_warning_inv)
         elif self.name and self.invisible and self.remaining_time1 == 0:
            pass			
         
      def on_block_destroy(self, x, y, z, mode):
         protocol = self.protocol
         if ((x, y, z) in self.protocol.santa_blocks) and self.name is not None:
            gift = ""
            val = random.randrange(1, 15)
            if val == 1 or val == 2:
               gift = "death"
               self.kill()
            elif val == 3:
               gift = "a dangerzone"
               self.airstrike = True
               self.refill()
               if self.kills < SCORE_REQUIREMENT:
                  self.kills = SCORE_REQUIREMENT
               self.dangerzone = True
               self.refill()
               self.send_chat('Dangerzone ready! Launch with e.g. /Dangerzone B4')
            elif val == 4 or val == 5:
               gift = "a restock"
               self.refill()
            elif val == 6 or val == 7 or val == 8:
               gift = "several grenades without the pin"
               self.spew_santa_grenades(x, y, z)
            elif val == 9 or val == 10 or val == 11:
               gift = "a grenade fountain"
               self.grenade_fountain(x, y, z)
            elif val == 12:
               gift = "30 seconds of flight"
               self.fly = True
               self.send_chat('Jump and rapidly press Ctrl to fly. Do NOT fly too high. Have fun!!')
               reactor.callLater(30, self.flight)
               reactor.callLater(22, self.countdown_warning_fly)
               self.remaining_time = 8
            elif val == 13:
               gift = "20 seconds of invisibility"
               self.invisible = True
               self.filter_visibility_data = True
               protocol.irc_say('* %s became invisible' % self.name)
               self.send_chat('You are now invisible... use it well.')
               reactor.callLater(20, self.invisibility)
               reactor.callLater(15, self.countdown_warning_inv)
               self.remaining_time1 = 5
            else:
               gift = "nothing"
            self.protocol.send_chat('%s opened one of Santa\'s presents and '
                              'received %s!' % (self.name, gift))
            self.protocol.irc_say('%s opened one of Santa\'s presents and '
                              'received %s!' % (self.name, gift))
         return connection.on_block_destroy(self, x, y, z, mode)

      def on_block_removed(self, x, y, z):
         if ((x, y, z) in self.protocol.santa_blocks):
            self.protocol.santa_blocks.discard((x, y, z))
         return connection.on_block_removed(self, x, y, z)
		 
      def on_kill(self, killer, type, grenade):
         self.fly = False
         self.invisible = False
         self.filter_visibility_data = False
         self.remaining_time = 0
         self.remaining_time1 = 0
         return connection.on_kill(self, killer, type, grenade)
		 
   class SantaProtocol(protocol):
      santa_blocks = set()
      
      def __init__(self, *arg, **kw):
         protocol.__init__(self, *arg, **kw)
         self.santa_gift_loop = LoopingCall(self.santa_drop)
         self.santa_gift_loop.start(45) # 5 minutes
		 
      def on_map_change(self, map):
         self.santa_blocks = set()
         return protocol.on_map_change(self, map)
   
      def santa_drop(self):
         """Spawns random blocks in the center of the map D4, D5, E4, E5"""
         if len(self.santa_blocks) > 6: # don't add anymore if there
            print "Too many gifts exist right now." # are more than 10.
            return

         block_num = random.randrange(2, 4)
         print "Attempting to place " + str(block_num) + " gifts"
         print str(len(self.santa_blocks)) + " gifts currently"
         for i in xrange(1, (block_num + 1)):
            x, y, z = self.get_random_location(True, (192, 192, 320, 320))
            z -= 1
            self.santa_drop_block(x, y, z)
            self.santa_blocks.add((x, y, z))
         self.send_chat('Santa just dropped off some goodies! Break the red blocks to open your gift!')
      
      def santa_drop_block(self, x, y, z):
         """Places a gift from Santa"""
         block_action = BlockAction()
         block_action.player_id = 32
         set_color = SetColor()
         set_color.value = 0xFF0000
         set_color.player_id = block_action.player_id
         self.send_contained(set_color, save = True)
         self.map.set_point(x, y, z, (255,0,0))
         block_action.value = BUILD_BLOCK
         set_color.value = 0xFF0000
         block_action.x = x
         block_action.y = y
         block_action.z = z
         self.send_contained(block_action, save = True)
         
   return SantaProtocol, SantaConnection

