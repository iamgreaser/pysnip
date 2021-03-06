import math
from twisted.internet import reactor
from pyspades.constants import *
from pyspades.collision import distance_3d_vector

class BaseWeapon(object):
    shoot = False
    reloading = False
    id = None
    shoot_time = None
    next_shot = None
    start = None
    
    def __init__(self, reload_callback):
        self.reload_callback = reload_callback
        self.reset()
        
    def restock(self):
        self.current_stock = self.stock
    
    def reset(self):
        self.shoot = False
        if self.reloading:
            self.reload_call.cancel()
            self.reloading = False
        self.current_ammo = self.ammo
        self.current_stock = self.stock
    
    def set_shoot(self, value):
        if value == self.shoot:
            return
        current_time = reactor.seconds()
        if value:
            self.start = current_time
            if self.current_ammo <= 0:
                return
            elif self.reloading and not self.slow_reload:
                return
            self.shoot_time = max(current_time, self.next_shot)
            if self.reloading:
                self.reloading = False
                self.reload_call.cancel()
        else:
            ammo = self.current_ammo
            self.current_ammo = self.get_ammo(True)
            self.next_shot = self.shoot_time + self.delay * (
                ammo - self.current_ammo)
        self.shoot = value
    
    def reload(self):
        if self.reloading:
            return
        ammo = self.get_ammo()
        if not self.current_stock or ammo >= self.ammo:
            return
        elif self.slow_reload and self.shoot and ammo:
            return
        self.reloading = True
        self.set_shoot(False)
        self.current_ammo = ammo
        self.reload_call = reactor.callLater(self.reload_time, self.on_reload)
    
    def on_reload(self):
        self.reloading = False
        if self.slow_reload:
            self.current_ammo += 1
            self.current_stock -= 1
            self.reload_callback()
            self.reload()
        else:
            new_stock = max(0, self.current_stock - (
                self.ammo - self.current_ammo))
            self.current_ammo += self.current_stock - new_stock
            self.current_stock = new_stock
            self.reload_callback()
    
    def get_ammo(self, no_max = False):
        if self.shoot:
            dt = reactor.seconds() - self.shoot_time
            ammo = self.current_ammo - max(0, int(
                math.ceil(dt / self.delay)))
        else:
            ammo = self.current_ammo
        if no_max:
            return ammo
        return max(0, ammo)
    
    def is_empty(self, tolerance = CLIP_TOLERANCE):
        return self.get_ammo(True) < -tolerance or not self.shoot
    
    def get_damage(self, value, position1, position2):
        if GAME_VERSION == 3:
            return self.damage[value]
        else:
            falloff = 1 - ((distance_3d_vector(position1, position2)**1.5)*0.0004)
            return math.ceil(self.damage[value] * falloff)

class Rifle(BaseWeapon):
    name = 'Rifle'
    delay = 0.5 if GAME_VERSION == 3 else 0.6
    ammo = 10 if GAME_VERSION == 3 else 8
    stock = 50 if GAME_VERSION == 3 else 48
    reload_time = 2.5
    slow_reload = False
    
    damage = {
        TORSO : 49,
        HEAD : 100,
        ARMS : 33,
        LEGS : 33
    } if GAME_VERSION == 3 else {
        TORSO : 60,
        HEAD : 1800,
        ARMS : 50,
        LEGS : 50
    }

class SMG(BaseWeapon):
    name = 'SMG'
    delay = 0.11 # actually 0.1, but due to AoS scheduling, it's usually 0.11
    ammo = 30
    stock = 120 if GAME_VERSION == 3 else 150
    reload_time = 2.5
    slow_reload = False
    
    damage = {
        TORSO : 29,
        HEAD : 75,
        ARMS : 18,
        LEGS : 18
    } if GAME_VERSION == 3 else {
        TORSO : 40,
        HEAD : 60,
        ARMS : 20,
        LEGS : 20
    }

class Shotgun(BaseWeapon):
    name = 'Shotgun'
    delay = 1.0 if GAME_VERSION == 3 else 0.8
    ammo = 6 if GAME_VERSION == 3 else 8
    stock = 48
    reload_time = 0.5 if GAME_VERSION == 3 else 0.4
    slow_reload = True
    
    damage = {
        TORSO : 27,
        HEAD : 37,
        ARMS : 16,
        LEGS : 16
    } if GAME_VERSION == 3 else {
        TORSO : 40,
        HEAD : 60,
        ARMS : 20,
        LEGS : 20
    }

class RiflePT(Rifle):
    pass # nothing we need to change here!

class SMGPT(SMG):
    delay = 0.075 # 1/15, scaled up a bit for scheduling reasons
    ammo = 20
    stock = 120
    reload_time = 5.0
    slow_reload = False
    
    damage = {
        TORSO : 30,
        HEAD : 34,
        ARMS : 21,
        LEGS : 21
    }

class ShotgunPT(Shotgun):
    # TODO: rebalance this!
    pass

WEAPONS = {
    RIFLE_WEAPON : Rifle,
    SMG_WEAPON : SMG,
    SHOTGUN_WEAPON : Shotgun,
    RIFLE_PT_WEAPON : RiflePT,
    SMG_PT_WEAPON : SMGPT,
    SHOTGUN_PT_WEAPON : ShotgunPT,
}

for id, weapon in WEAPONS.iteritems():
    weapon.id = id

