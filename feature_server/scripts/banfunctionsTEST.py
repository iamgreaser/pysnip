from twisted.internet.reactor import seconds
from pyspades.collision import distance_3d_vector
from pyspades.server import position_data
from pyspades.constants import *
from commands import name, get_player, add, admin, alias
import commands
import math
    
def apply_script(protocol, connection, config):
    class banfunctionsConnection(connection):
        dist1 = ""
        weap1 = ""
        prev_time1 = None
        prev_illegal_dt = None
        prev_smg_snap = None
        prev_nospread = None
        prev_recoil_test_time = None
        recoil_test_timer = 0 
        junction2 = False
        body_part1 = ""
        illegal_dt_count = 0
        smg_snap_count = 0
        no_recoil_event_count = 0
        shotgun_nospread_count = 0
        howmuchammoisinmyclip = 0 
        prevdist = None
        presdist = None
        Theta = 0
        prev_xyz = None 
        prevtarget = ""
        prev_body_part = None  
        spread_hs_count, spread_bs_count, spread_ls_count = 0, 0, 0
        spread_hit_type, spread_hit_player = None, None        
            
        def on_hit(self, hit_amount, hit_player, type, grenade):
            body_damage_values = [49, 29, 27]
            limb_damage_values =  [33, 18, 16]
            if type == HEADSHOT_KILL or hit_amount in body_damage_values or hit_amount in limb_damage_values:
                if not grenade:

                    dist1 = int(distance_3d_vector(self.world_object.position, hit_player.world_object.position))
                    
                    weap1 = self.weapon_object.name
                    self.pres_time1 = seconds()

                    if self.prev_time1 is None:
                        dt1 = None
                    else: dt1 = (self.pres_time1 - self.prev_time1) * 1000
                    self.prev_time1 = seconds()

                    if type == HEADSHOT_KILL:
                        body_part1 = "HEADSHOT"
                    elif hit_amount in body_damage_values:
                        body_part1 = "Body"
                    elif hit_amount in limb_damage_values:
                        body_part1 = "Limb"
                     
                    self.presdist = dist1
                    if dt1 is not None and dt1 < 3000 and self.prev_xyz is not None:
                        if self.prev_xyz == hit_player.world_object.position:
                            theta = 0
                        else:
                            target2target_dist =  int(distance_3d_vector(hit_player.world_object.position, self.prev_xyz))
                            theta = int(math.acos((self.presdist ** 2 + self.prevdist ** 2 - target2target_dist ** 2) / (2 * self.presdist * self.prevdist)))
                            theta = math.degrees(theta)
                        
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
                            else:
                                self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                                self.spread_hit_type, self.spread_hit_player = body_part1, hit_player.name             
                        else:  
                            self.spread_hs_count, self.spread_bs_count, self.spread_ls_count = 0, 0, 0
                            self.spread_hit_type, self.spread_hit_player = None, None
                    if self.spread_hs_count >= 7 or self.spread_bs_count >= 7 or self.spread_ls_count >= 7:
                        self.shotgun_nospread_count += 1
                        self.pres_nospread = seconds()
                        if self.prev_nospread is None:
                            nospread_timer = 0
                        else: nospread_timer = (self.pres_nospread - self.prev_nospread)
                        self.prev_nospread = seconds()
                        if nospread_timer >= 30:
                                self.shotun_nospread_count = 1
                    if self.shotgun_nospread_count >= 3:
                        self.ban('Hack Detected - No Spread    IGN: %s' % (self.name), 10080)
                        return False     
                    if weap1 == "SMG" or weap1 == "Rifle":
                        if dt1 is not None and dt1  < 5:
                            self.illegal_dt_count += 1
                            self.pres_illegal_dt = seconds()
                            if self.prev_illegal_dt is None:
                                dt_timer = 0
                            else: dt_timer = (self.pres_illegal_dt - self.prev_illegal_dt)
                            self.prev_illegal_dt = seconds()
                            if dt_timer >= 60:
                                self.illegal_dt_count = 1
                    if self.illegal_dt_count >= 7:
                        self.ban('Hack Detected - Multiple Bullets    IGN: %s' % (self.name), 10080)
                        return False   
                    
                    if weap1 == "SMG"  and dist1 >= 15 and self.prevdist >= 15:
                        if dt1 is not None and dt1 >= 5 and dt1 < 155:
                            if hit_player.name != self.prevtarget and body_part1 == self.prev_body_part: 
                                if theta >= 10:
                                    self.smg_snap_count += 1
                                    if theta >= 45:
                                        self.smg_snap_count +=1
                                        if theta >= 90:
                                            self.smg_snap_count += 1     
                                    self.pres_smg_snap = seconds()
                                    if self.prev_smg_snap is None:
                                        smg_snap_timer = 0
                                    else: smg_snap_timer = (self.pres_smg_snap - self.prev_smg_snap)
                                    if smg_snap_timer >= 60:
                                        self.smg_snap_count = 1
                    if self.smg_snap_count >= 4:
                        self.ban('Hack Detected - Aimbot    IGN: %s' % (self.name), 10080)                
                        return False              
                         
                    self.prevtarget = hit_player.name
                    self.prev_body_part = body_part1  
                    self.prevdist = dist1
                    self.prev_xyz = hit_player.world_object.position
                                       
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)

        def on_shoot_set(self, fire):
            if self.tool == WEAPON_TOOL:
                self.pres_recoil_test_time = seconds()
                if self.prev_recoil_test_time is None:
                    self.recoil_test_timer = .75
                else: self.recoil_test_timer = self.pres_recoil_test_time - self.prev_recoil_test_time
                if self.recoil_test_timer >= .75:  
                    if fire:
                        self.set_start_orientX, self.set_start_orientY, self.set_start_orientZ = round(self.world_object.orientation.x, 10), round(self.world_object.orientation.y, 10), round(self.world_object.orientation.z, 10)
                        self.send_chat('Junction 1 confirmed')
                        self.howmuchammoisinmyclip =  self.weapon_object.current_ammo
                        print self.howmuchammoisinmyclip
                        self.junction2 = True       
                    if not fire and self.junction2:
                        self.set_end_orientX, self.set_end_orientY, self.set_end_orientZ = round(self.world_object.orientation.x, 10), round(self.world_object.orientation.y, 10), round(self.world_object.orientation.z, 10)
                        self.prev_recoil_test_time = seconds()
                        self.send_chat('Junction 2 confirmed')
                        self.junction2 = False
                        if self.set_start_orientX == self.set_end_orientX and self.set_start_orientY == self.set_end_orientY and self.set_start_orientZ == self.set_end_orientZ:
                            print self.weapon_object.current_ammo 
                            if self.howmuchammoisinmyclip != self.weapon_object.current_ammo and self.howmuchammoisinmyclip > 1:  
                                self.no_recoil_event_count += 1
                                self.send_chat('event +1')
                        else: self.no_recoil_event_count = 0 
                        if self.no_recoil_event_count >= 3:
                            self.irc_say('Possible Hack Detected - No Recoil    IGN: %s' % (self.name))
                  
            return connection.on_shoot_set(self, fire)    
       
    return protocol, banfunctionsConnection