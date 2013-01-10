from twisted.internet.reactor import seconds
from pyspades.collision import distance_3d_vector
from pyspades.server import position_data
from pyspades.constants import *
from commands import name, get_player, add, admin, alias
import commands

@name('analyze')
@alias('an')
def analyze_shot(connection, player = None):
    protocol = connection.protocol
    if player is None:
        connection.local_variable = protocol.players
        for people in connection.local_variable.itervalues():
            if connection.name in people.shots_analyzed_by:
                people.shots_analyzed_by.remove(connection.name)
                connection.send_chat("You are no longer analyzing anyone.")
    else:
        player = get_player(protocol, player)
        if player not in protocol.players:
            raise ValueError()
        else:
            if not player.shots_analyzed_by:
                player.shots_analyzed_by = []
            connection.local_variable = protocol.players
            for person in connection.local_variable.itervalues():
                if person.name is None:
                    continue
                if person != player and connection.name in person.shots_analyzed_by:
                    person.shots_analyzed_by.remove(connection.name)
                    connection.send_chat("You are no longer analyzing %s." % (person.name))
                    print person.shots_analyzed_by
            if connection.name not in player.shots_analyzed_by:
                connection.send_chat("You are now analyzing %s." % (player.name))
                player.shots_analyzed_by.append(connection.name)
                connection.hs, connection.bs, connection.ls = 0, 0, 0
                print player.shots_analyzed_by
            elif connection.name in player.shots_analyzed_by:
                connection.send_chat("You are no longer analyzing anyone.")
                player.shots_analyzed_by.remove(connection.name)
                print player.shots_analyzed_by
        
add(analyze_shot)
def apply_script(protocol, connection, config):
    class analyze_shotsConnection(connection):
        dist = ""
        weap = ""
        shots_analyzed_by = []
        local_variable = []
        hs, bs, ls = 0, 0, 0
        prev_time = None
        illegal_dt_count = 0
        spread_hs_count, spread_bs_count, spread_ls_count = 0, 0, 0
        spread_hit_amount, spread_hit_player = None, None
        
        def on_hit(self, hit_amount, hit_player, type, grenade):
            body_damage_values = [49, 29, 27]
            limb_damage_values =  [33, 18, 16]
            dist = int(distance_3d_vector(self.world_object.position, hit_player.world_object.position))
            weap = self.weapon_object.name
            self.pres_time = seconds()
            if self.prev_time is None:
                dt = None
            else: dt = (self.pres_time - self.prev_time) * 1000
            self.prev_time = seconds()
            if weap == "SMG" or weap == "Rifle":
                if dt is not None and dt  < 5:
                    self.illegal_dt_count = self.illegal_dt_count + 1
            if weap == "Shotgun":
                if dist > 20:
                    if dt < 8:
                        if hit_amount == self.spread_hit_amount and hit_player.name == self.spread_hit_player:
                            if type == HEADSHOT_KILL:
                                self.spread_hs_count = self.spread_hs_count +1
                            elif hit_amount in body_damage_values:
                                self.spread_hs_count = self.spread_bs_count +1
                            elif hit_amount in limb_damage_values:
                                self.spread_ls_count = self.spread_ls_count +1
                        else: 
                            self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                            self.spread_hit_amount, self.spread_hit_player = None, None 
                    else:
                        self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                        self.spread_hit_amount, self.spread_hit_player = hit_amount, hit_player.name             
                else:  
                     self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                     self.spread_hit_amount, self.spread_hit_player = None, None
            self.local_variable = self.shots_analyzed_by
            for names in self.local_variable:
                adminz = get_player(self.protocol, names)
                if type == HEADSHOT_KILL:
                    adminz.hs = adminz.hs + 1
                    if dt is not None:
                        adminz.send_chat('%s shot %s dist: %d blocks dT: %.0f ms %s HEADSHOT(%d)' % (self.name, hit_player.name, dist, dt, weap, adminz.hs))
                    else:
                        adminz.send_chat('%s shot %s dist: %d blocks dT: NA %s HEADSHOT(%d)' % (self.name, hit_player.name, dist, weap, adminz.hs))
                if hit_amount in body_damage_values:
                    adminz.bs = adminz.bs + 1
                    if dt is not None:
                        adminz.send_chat('%s shot %s dist: %d blocks dT: %.0f ms %s Body(%d)' % (self.name, hit_player.name, dist, dt, weap, adminz.bs))
                    else:
                        adminz.send_chat('%s shot %s dist: %d blocks dT: NA %s Body(%d)' % (self.name, hit_player.name, dist, weap, adminz.bs))
                if hit_amount in limb_damage_values:
                    adminz.ls = adminz.ls + 1
                    if dt is not None:
                        adminz.send_chat('%s shot %s dist: %d blocks dT: %.0f ms %s Limb(%d)' % (self.name, hit_player.name, dist, dt, weap, adminz.ls))
                    else:
                        adminz.send_chat('%s shot %s dist: %d blocks dT: NA %s Limb(%d)' % (self.name, hit_player.name, dist, weap, adminz.ls))
            if self.illegal_dt_count >= 5:
                self.ban('Hack Detected - Multiple Bullets', 10080)
                return False
            if self.spread_hs_count >= 7 or self.spread_bs_count >= 7 or self.spread_ls_count >=7:
                self.ban('Hack Detected - No Spread', 10080)
                return False                      
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)             
                       
        def on_disconnect(self):
            self.illegal_dt_count = 0
            if self.shots_analyzed_by:
                self.local_variable = self.shots_analyzed_by 
                for names in self.local_variable:
                    adminz = get_player(self.protocol, names)
                    if names != self.name: 
                        adminz.send_chat("No longer analyzing %s.  Player has disconnected." % (self.name))
            self.shots_analyzed_by = []
            self.prev_time = None
            self.local_variable = self.protocol.players
            for player in self.local_variable.itervalues():
                if self.name in player.shots_analyzed_by:
                    player.shots_analyzed_by.remove(self.name)
            return connection.on_disconnect(self)
    
    
    return protocol, analyze_shotsConnection
            
                                            

     
