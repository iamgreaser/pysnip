"""
Makes a cordinate to a dangerzone
where everyone will exploade in that cordinate.
inspred by the move Battle Royal


Credit to: 
    Hompy for letting me borrow the airsrtrike code and lot's of help
    triplefox for map_extensions.py
    Danko for Nadesplotion
    Dany0 and mat^2 for some help

Maintainer: Enari
"""

from math import ceil
from random import randrange, uniform
from twisted.internet.reactor import callLater, seconds
from pyspades.server import orientation_data, grenade_packet
from pyspades.common import coordinates, to_coordinates, Vertex3
from pyspades.collision import distance_3d_vector
from pyspades.world import Grenade
from pyspades.constants import GRENADE_KILL, GRENADE_DESTROY
from pyspades import contained as loaders
from commands import alias, add


SCORE_REQUIREMENT = 15
STREAK_REQUIREMENT = 15
TEAM_COOLDOWN = 80
DANGERZONE_DURATION = 60
EVAC_TIME = 7
REFILL_ON_DANGERZONE = True # set to False if you don't want to be healed

block_action = loaders.BlockAction()

S_READY = 'Dangerzone ready! Launch with e.g. /Dangerzone B4'
S_NO_SCORE = 'You need a total score of {score} (kills or intel) to ' \
    'unlock dangerzones!'
S_NO_STREAK = 'Every {streak} consecutive kills (without dying) you get an ' \
    'dangerzone. {remaining} kills to go!'
S_BAD_COORDS = "Bad coordinates: should be like 'A4', 'G5'. Look them up in the map"
S_COOLDOWN = '{seconds} seconds before your team can make another dangerzone'
S_DZ_START = '{player} made location {coords} to a Dangerzone!'
S_DZ_GETOUT = 'You have {seconds} seconds to get out!'
S_DZ_NOWDZ = '{coords} is now a Dangerzone'
S_UNLOCKED = 'You have unlocked Dangerzone!'
S_UNLOCKED_TIP = 'Each {streak}-kill streak will clear you for one dangerzone'
S_DZ_END = '{coords} is no longer a Dangerzone'
S_IN_DZ = 'You are in a Dangerzone, get out!'

@alias('airstrike')
@alias('dz')
def dangerzone(connection, coords = None):
    protocol = connection.protocol
    if connection not in protocol.players:
        raise ValueError()
    player = connection
    if not coords and player.dangerzone:
        return S_READY
    if player.kills < SCORE_REQUIREMENT:
        return S_NO_SCORE.format(score = SCORE_REQUIREMENT)
    elif not player.dangerzone:
        kills_left = STREAK_REQUIREMENT - (player.streak % STREAK_REQUIREMENT)
        return S_NO_STREAK.format(streak = STREAK_REQUIREMENT,
            remaining = kills_left)
    try:
        coord_x, coord_y = coordinates(coords)
    except (ValueError):
        return S_BAD_COORDS
    last_dangerzone = getattr(player.team, 'last_dangerzone', None)
    if last_dangerzone and seconds() - last_dangerzone < TEAM_COOLDOWN:
        remaining = TEAM_COOLDOWN - (seconds() - last_dangerzone)
        return S_COOLDOWN.format(seconds = int(ceil(remaining)))
    player.start_dangerzone(coord_x, coord_y)

add(dangerzone)

def apply_script(protocol, connection, config):
    class dangerzoneConnection(connection):
        dangerzone = False
        last_streak = None
        
        def start_dangerzone(self, coord_x, coord_y):
            print "start_dangerzone"
            coords = to_coordinates(coord_x, coord_y)
            message = S_DZ_START.format(player = self.name, coords = coords)
            self.protocol.send_chat(message)
            message = S_DZ_GETOUT.format(seconds = EVAC_TIME)
            self.protocol.send_chat(message)
            
            self.team.last_dangerzone = seconds()
            self.dangerzone = False
            
            self.protocol.dz_x = coord_x
            self.protocol.dz_y = coord_y
            if self.name is None:
                return
            self.protocol.dangerzone_on = True
            callLater(EVAC_TIME, self.do_dangerzone)
            callLater(DANGERZONE_DURATION, self.end_dangerzone)
        
        def do_dangerzone(self):
            print("do_dangerzone")
            coords = to_coordinates(self.protocol.dz_x, self.protocol.dz_y)
            message = S_DZ_NOWDZ.format(coords = coords)
            self.protocol.send_chat(message)
            callLater(0.5, self.dangerzone_damage)
                
        def dangerzone_damage(self):
            if self.protocol.dangerzone_on == False:
                return
            for player in self.protocol.players.values():
                if player.world_object is not None and player.world_object.dead == False:
                    x, y, z = player.get_location()
                    if (x>= self.protocol.dz_x and x<= (self.protocol.dz_x + 64) and 
                        y>= self.protocol.dz_y and y<= (self.protocol.dz_y + 64)):
                        player.send_chat(S_IN_DZ)
                        self.nadesplode(player)
            callLater(1, self.dangerzone_damage)
            
        def nadesplode(self, hit_player):
            self.protocol.world.create_object(Grenade, 0.0, hit_player.world_object.position, None, Vertex3(), self.nadepl_exploded)
            grenade_packet.value = 0.1
            grenade_packet.player_id = self.player_id
            grenade_packet.position = (hit_player.world_object.position.x, hit_player.world_object.position.y, hit_player.world_object.position.z)
            grenade_packet.velocity = (0.0, 0.0, 0.0)
            self.protocol.send_contained(grenade_packet)
            
        def nadepl_exploded(self, grenade):
            if self.name is None or self.team.spectator:
                return
            if grenade.team is not None and grenade.team is not self.team:
                # could happen if the player changed team
                return
            position = grenade.position
            x = position.x
            y = position.y
            z = position.z
            if x < 0 or x > 512 or y < 0 or y > 512 or z < 0 or z > 63:
                return
            x = int(x)
            y = int(y)
            z = int(z)
            for player in self.team.other.get_players():
                if not player.hp:
                    continue
                if (player.world_object.position.x <= (x + 2) and player.world_object.position.x >= (x - 2) and
                    player.world_object.position.y <= (y + 2) and player.world_object.position.y >= (y - 2) and
                    player.world_object.position.z <= (z + 2) and player.world_object.position.z >= (z - 2)):
                        player.set_hp(player.hp - 16, self, 
                        hit_indicator = position.get(), type = GRENADE_KILL,
                        grenade = grenade)
            if self.on_block_destroy(x, y, z, GRENADE_DESTROY) == False:
                return
            map = self.protocol.map
            for nade_x in xrange(x - 1, x + 2):
                for nade_y in xrange(y - 1, y + 2):
                    for nade_z in xrange(z - 1, z + 2):
                        if map.destroy_point(nade_x, nade_y, nade_z):
                            self.on_block_removed(nade_x, nade_y, nade_z)
            block_action.x = x
            block_action.y = y
            block_action.z = z
            block_action.value = GRENADE_DESTROY
            block_action.player_id = self.player_id
            self.protocol.send_contained(block_action, save = True)
            self.protocol.update_entities()
             
        
        def end_dangerzone(self):
            coords = to_coordinates(self.protocol.dz_x, self.protocol.dz_y)
            message = S_DZ_END.format(coords = coords)
            self.protocol.send_chat(message)
            self.protocol.dangerzone_on = False	
            
        def on_kill(self, killer, type, grenade):
            self.dangerzone = False
            self.last_streak = None
            connection.on_kill(self, killer, type, grenade)
            
        def add_score(self, score):
            connection.add_score(self, score)
            score_met = (self.kills >= SCORE_REQUIREMENT)
            streak_met = (self.streak >= STREAK_REQUIREMENT)
            if not score_met:
                return
            just_unlocked = False
            if self.kills - score < SCORE_REQUIREMENT:
                self.send_chat(S_UNLOCKED)
                self.send_chat(S_UNLOCKED_TIP.format(streak = STREAK_REQUIREMENT))
                just_unlocked = True
            if not streak_met:
                return
            if ((self.streak % STREAK_REQUIREMENT == 0 or just_unlocked) and
                self.streak != self.last_streak):
                self.send_chat(S_READY)
                self.dangerzone = True
                self.last_streak = self.streak
                if REFILL_ON_DANGERZONE:
                    self.refill()

    class dangerzoneProtocol(protocol):
        dangerzone_on = False
        dz_x = dz_y = 0
    
    return dangerzoneProtocol, dangerzoneConnection
