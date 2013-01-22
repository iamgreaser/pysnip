from twisted.internet.reactor import seconds
from pyspades.collision import distance_3d_vector
from pyspades.server import position_data
from pyspades.constants import *
from commands import name, get_player, add, admin, alias
import commands
from math import acos, degrees, sqrt


def apply_script(protocol, connection, config):
    class aimbotsnatcherConnection(connection):
        previous_vector = None
        previous_orient_clock = 0
        previous_vector = None
        snap_theta = 0
        lock_kill = 0
        dist_thresh = 0
        snap_gate = False
        aim_lock = False

        def vector_angle(self, vec1, vec2):
            a = self.distance((0, 0, 0), vec1)
            b = self.distance((0, 0, 0), vec2)
            c = self.distance(vec1, vec2)
            cosc = (a **2 + b ** 2 - c ** 2) / (2 * a * b)
            if cosc < -1:
                cosc  = -1
            elif cosc > 1:
                cosc = 1
            data = acos(cosc) 
            return degrees(data)
                
        def distance(self, pos1, pos2):
            c = (pos1[0] - pos2[0]) **2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2
            return sqrt(c)
			
        def snap_analysis(self):
            self.orient_clock = seconds()
            self.present_vector = (self.world_object.orientation.x, self.world_object.orientation.y, self.world_object.orientation.z)
            if self.previous_vector is not None:
                self.snap_theta = self.vector_angle(self.present_vector, self.previous_vector)
                self.elapsed_time = (self.orient_clock - self.previous_orient_clock)
                if self.elapsed_time <= 1 and self.snap_theta >= 5 and self.snap_gate == False:
                    self.snap_gate = True
                    self.snap_angle = self.snap_theta 
                    self.dist_thresh = 0
                elif self.elapsed_time <= .5 and self.snap_theta <= .9 and self.snap_gate == True:
                    if self.dist_thresh == 0:
                        self.dist_thresh = (self.snap_theta * -126) + 160
                    elif (self.snap_theta * -126) + 160 > self.dist_thresh:
                        self.dist_thresh = (self.snap_theta * -126) + 160
                    self.aim_lock = True
                else:
                    self.snap_gate = False
                    self.aim_lock = False
                    self.dist_thresh = 0
                    self.snap_angle = 0
            self.previous_vector = self.present_vector
            self.previous_orient_clock = self.orient_clock
            return

        def on_orientation_update(self, x, y, z):
            self.snap_analysis()
            return connection.on_orientation_update(self, x, y, z)

        def on_kill(self, killer, type, grenade):
            if killer is not None and grenade is None:
                killer.target_position = (self.world_object.position.x, self.world_object.position.y, self.world_object.position.z)
                killer.killer_position = (killer.world_object.position.x, killer.world_object.position.y, killer.world_object.position.z)
                killer.kill_distance = self.distance(killer.target_position, killer.killer_position)		
                if killer.aim_lock == True and killer.kill_distance >= 20 and killer.kill_distance <= killer.dist_thresh:
                    killer.lock_kill += 1
                    irc_relay = killer.protocol.irc_relay
                    message = 'Lock Kill Event Detected: %s #%s (%s) Weapon: %s Ping: %d ms Snap Angle: %.2f Distance: %.1f (%d)' % (killer.name, killer.player_id, killer.address[0], killer.weap1, killer.latency, killer.snap_angle, killer.kill_distance, killer.lock_kill)
                    for adminz in self.protocol.players.values():
                        if adminz.admin:
                            adminz.send_chat(message) 					
                    if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                        message = '\x0304' + message + '\x0f'
                    irc_relay.send(message)
            return connection.on_kill(self, killer, type, grenade)
			
    return protocol, aimbotsnatcherConnection			