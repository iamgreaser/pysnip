from twisted.internet.reactor import callLater, seconds
from pyspades.collision import distance_3d_vector
from pyspades.server import position_data
from pyspades.constants import *
from commands import name, get_player, add, admin, alias
import commands
import time
from math import acos, degrees, sqrt
    
def apply_script(protocol, connection, config):
    class banfunctionsConnection(connection):
        dist1 = ""
        weap1 = ""
        prev_time1 = None
        prev_illegal_dt = None
        prev_smg_snap = None
        prev_nospread = None
        body_part1 = ""
        illegal_dt_count = 0
        smg_snap_count = 0
        shotgun_nospread_count = 0 
        dt_reset_count = 0
        dt_event_count = 0
        mb_event_count = 0	
        prevdist = None
        presdist = None
        positionz = (0, 0, 0)
        theta = 0
        prev_xyz = None 
        prevtarget = ""
        prev_body_part = None   
        spread_hs_count, spread_bs_count, spread_ls_count = 0, 0, 0
        spread_hit_type, spread_hit_player = None, None
        orient_count = 0
        junction = False
        start_set_time = seconds()
        end_set_time = seconds()
        nr_reset_count = 0
        nr_count = 0
        start_ammo = None

        def mb_report(self):
            if self.name and self.dt_event_count != 0:
                self.mb_event_count  += 1		
            if self.name and self.dt_event_count >= 2:
                self.dt_event_count += 1
                message = 'Multiple Bullets Event Detected: %s #%s (%s) Ping: %d ms  At least %d bullets fired at once.' % (self.name, self.player_id, self.address[0], self.latency, self.dt_event_count)
                irc_relay = self.protocol.irc_relay 
                if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                    message = '\x0304' + message + '\x0f'
                irc_relay.send(message)
                self.dt_event_count = 0
            if self.name and self.illegal_dt_count >= 8 and self.mb_event_count >= 4:
                self.illegal_dt_count = 0
                self.dt_reset_count = 0
                self.mb_event_count = 0
                self.ban('Hack Detected - Multiple Bullets  IGN: %s #%d' % (self.name, self.player_id), 0)
                return False
                
                
            
        def on_hit(self, hit_amount, hit_player, type, grenade):
            body_damage_values = [49, 29, 27]
            limb_damage_values =  [33, 18, 16]

            def vector_angle(self, vec1, vec2): 
                a = distance(self, self.positionz, vec1)
                b = distance(self, self.positionz, vec2)
                c = distance(self, vec1, vec2)
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
           
            if type == HEADSHOT_KILL or hit_amount in body_damage_values or hit_amount in limb_damage_values:
                if not grenade:

                    curx, cury, curz = self.world_object.position.x, self.world_object.position.y, self.world_object.position.z
                    self.positionz = (curx, cury, curz)
                     
                    tarx, tary, tarz = hit_player.world_object.position.x, hit_player.world_object.position.y, hit_player.world_object.position.z
                    targetpos = (tarx, tary, tarz)      
                    
                    dist1 = distance(self, self.positionz, targetpos)
                    
                    weap1 = self.weapon_object.name
                    self.pres_time1 = seconds()     

                    if self.prev_time1 is None:
                        dt1 = None
                    else: dt1 = (self.pres_time1 - self.prev_time1) * 1000
                    self.prev_time1 = self.pres_time1
                    if type == HEADSHOT_KILL:
                        body_part1 = "HEADSHOT"
                    elif hit_amount in body_damage_values:
                        body_part1 = "Body"
                    elif hit_amount in limb_damage_values:
                        body_part1 = "Limb"
                     
                    self.presdist = dist1
                    if dt1 is not None and dt1 < 3000 and self.prev_xyz is not None:
                        if self.prev_xyz == hit_player.world_object.position or self.prevtarget == hit_player.name:
                            theta = 0
                        else:
                            theta = vector_angle(self, self.prev_xyz, targetpos)
                        
                    if weap1 == "Shotgun":
                        if dist1 > 23:
                            if dt1 < 8:
                                if body_part1 == self.spread_hit_type and hit_player.name == self.spread_hit_player:
                                    if body_part1 == "HEADSHOT":
                                        self.spread_hs_count += 1
                                    elif body_part1 == "Body":
                                        self.spread_bs_count += 1
                                    elif body_part1 == "Limb":
                                        self.spread_ls_count += 1
                                else: 
                                    self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                                    self.spread_hit_type, self.spread_hit_player = None, None
                                    if self.shotgun_nospread_count >= 1:
                                        message = 'No-spread count for player %s #%s (%s) has been reset.  The player either turned off his hack, or the previous event was a false positive.' % (self.name, self.player_id, self.address[0])
                                        irc_relay = self.protocol.irc_relay 
                                        if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                                            message = '\x0304' + message + '\x0f'
                                        irc_relay.send(message)
                                        self.shotgun_nospread_count = 0 
                            else:
                                self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                                self.spread_hit_type, self.spread_hit_player = body_part1, hit_player.name             
                        else:  
                            self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                            self.spread_hit_type, self.spread_hit_player = None, None
                        if self.spread_hs_count >= 7 or self.spread_bs_count >= 7 or self.spread_ls_count >= 7:
                            self.shotgun_nospread_count += 1
                            self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                            message = 'No Spread Event Detected: %s #%s (%s)' % (self.name, self.player_id, self.address[0])
                            irc_relay = self.protocol.irc_relay 
                            if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                                message = '\x0304' + message + '\x0f'
                            irc_relay.send(message)  
                            self.pres_nospread = seconds()
                            if self.prev_nospread is None:
                                nospread_timer = 0
                            else: nospread_timer = (self.pres_nospread - self.prev_nospread)
                            self.prev_nospread = self.pres_nospread
                            if nospread_timer >= 600:
                                    self.shotun_nospread_count = 1
                            elif self.shotgun_nospread_count >= 3:
                                self.ban('Hack Detected - No Spread    IGN: %s #%d' % (self.name, self.player_id), 0) #this ban is for the shotty no spread hack. 0 minutes = Permanent
                                return False     

                    if weap1 == "SMG" or weap1 == "Rifle":
                        if dt1 is not None and dt1  < 10:
                            self.illegal_dt_count += 1
                            self.dt_event_count += 1
                            callLater(0.02, self.mb_report) 
                            self.dt_reset_count = 0 
                            self.pres_illegal_dt = seconds()
                            if self.prev_illegal_dt is None:
                                dt_timer = 0
                            else: dt_timer = (self.pres_illegal_dt - self.prev_illegal_dt)
                            self.prev_illegal_dt = seconds()
                            if dt_timer >= 30:
                                self.illegal_dt_count = 1
                                self.mb_event_count = 0
                        elif dt1 >= 10:
                            self.dt_reset_count += 1
                            self.dt_event_count = 0
                            if self.dt_reset_count >= 2:
                                self.illegal_dt_count = 0
                                self.dt_reset_count = 0
                                self.mb_event_count = 0						

                    if weap1 == "SMG"  and dist1 >= 15 and self.prevdist >= 15:
                        if dt1 is not None and dt1 >= 5 and dt1 < 155:
                            if hit_player.name != self.prevtarget and body_part1 == self.prev_body_part: 
                                if theta >= 10:
                                    self.smg_snap_count += 1
                                    message = 'SMG Snap Detected: %.2f degrees. %s #%s (%s)' % (theta, self.name, self.player_id, self.address[0])
                                    for adminz in self.protocol.player.values():
                                        if adminz.admin:
                                            adminz.send_chat(message)
                                    irc_relay = self.protocol.irc_relay 
                                    if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                                        message = '\x0304' + message + '\x0f'
                                    irc_relay.send(message)
                                    if theta >= 20:
                                        self.smg_snap_count += 1	
                                        if theta >= 35:
                                            self.smg_snap_count +=2
                                            if theta >= 60:
                                                self.smg_snap_count += 3     
                                    self.pres_smg_snap = seconds()
                                    if self.prev_smg_snap is None:
                                        smg_snap_timer = 0
                                    else: smg_snap_timer = (self.pres_smg_snap - self.prev_smg_snap)
                                    if smg_snap_timer >= 180:
                                        self.smg_snap_count = 1
                    if self.smg_snap_count >= 7:
                        self.ban('Hack Detected - Aimbot    IGN: %s, #%d' % (self.name, self.player_id), 10080)               
                        return False     
                    self.prevtarget = hit_player.name
                    self.prev_body_part = body_part1  
                    self.prevdist = dist1
                    self.prev_xyz = targetpos                     
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)

        def on_weapon_set(self, value):
            self.shotun_nospread_count = 0
            self.illegal_dt_count = 0
            self.smg_snap_count = 0
            return connection.on_weapon_set(self, value)

        def on_orientation_update(self, x, y, z):
            callLater(.005, self.orientationcount)
            return connection.on_orientation_update(self, x, y, z)

        def orientationcount(self):
            self.orient_count += 1
            return
			
        def on_shoot_set(self, fire):
            self.fire = fire
            if self.tool == WEAPON_TOOL:
                self.weap1 = self.weapon_object.name
                if self.fire and seconds() - self.start_set_time >= 1 and seconds() - self.end_set_time >= 1:
                    self.start_ammo = self.weapon_object.current_ammo
                    self.orient_count = 0
                    self.junction = True
                    self.start_set_time = seconds()
                elif not self.fire and self.junction and seconds() - self.start_set_time >= .05 and self.world_object.orientation.z >= -0.95 and self.world_object.orientation.z <= 0.95:
                    self.end_set_time = seconds()
                    callLater(0.05, self.recoiltest)
                elif not self.fire and self.start_ammo != self.weapon_object.current_ammo:
                    self.junction = False
            return connection.on_shoot_set(self, fire)
		
        def recoiltest(self):
            self.shots_fired = self.start_ammo - self.weapon_object.current_ammo
            if self.start_ammo != self.weapon_object.current_ammo and self.weap1 != "SMG" and self.weapon_object.current_ammo != 0:
                if self.shots_fired == 1 and self.shots_fired > self.orient_count:
                    self.nr_count += 1
                    if self.nr_count >= 4:
                        self.nr_count = 0
                        message = 'No Recoil Event(s) Detected: %s #%s (%s) Weapon: %s Ping: %d ms' % (self.name, self.player_id, self.address[0], self.weap1, self.latency)
                        irc_relay = self.protocol.irc_relay
                        for adminz in self.protocol.players.values():
                            if adminz.admin:
                                adminz.send_chat(message)
                        if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                            message = '\x0304' + message + '\x0f'
                        irc_relay.send(message)
                    self.junction = False
                    return
                elif self.shots_fired >= 2 and self.shots_fired - self.orient_count >= 2:
                    message = 'No Recoil Event(s) Detected: %s #%s (%s) Weapon: %s Ping: %d ms' % (self.name, self.player_id, self.address[0], self.weap1, self.latency)
                    irc_relay = self.protocol.irc_relay
                    for adminz in self.protocol.players.values():
                        if adminz.admin:
                            adminz.send_chat(message)
                    if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                        message = '\x0304' + message + '\x0f'
                    irc_relay.send(message)
                    self.nr_reset_count = 0
                    self.junction = False
                    return
                elif self.shots_fired == self.orient_count:
                    self.nr_reset_count += 1
                    if self.nr_reset_count >= 3:
                        self.nr_count = 0
                        self.nr_reset_count = 0
                    self.junction = False
                    return
            elif self.start_ammo != self.weapon_object.current_ammo and self.weap1 == "SMG":
                if self.shots_fired >= 6:
                    self.shots_without_recoil = self.shots_fired - self.orient_count
                    self.no_recoil_percentage = self.shots_without_recoil * 100 / self.shots_fired
                    if self.no_recoil_percentage >= 70:
                        message = 'No Recoil Event(s) Detected: %s #%s (%s) Weapon: %s Ping: %d ms' % (self.name, self.player_id, self.address[0], self.weap1, self.latency)
                        irc_relay = self.protocol.irc_relay
                        for adminz in self.protocol.players.values():
                            if adminz.admin:
                                adminz.send_chat(message)
                        if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                            message = '\x0304' + message + '\x0f'
                        irc_relay.send(message)
                self.junction = False
                return
    return protocol, banfunctionsConnection
