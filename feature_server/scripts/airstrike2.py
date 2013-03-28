"""
Airstrikes. Boom!

Maintainer: hompy
"""

from math import ceil, sin, cos
from random import randrange, uniform, vonmisesvariate
from twisted.internet.reactor import callLater, seconds
from pyspades.server import orientation_data, grenade_packet, set_hp, weapon_reload
from pyspades.common import coordinates, to_coordinates, Vertex3
from pyspades.collision import distance_3d_vector
from pyspades.world import Grenade
from pyspades.constants import *
from commands import alias, add

STREAK_REQUIREMENT = 8

HEAL_ON_GRANT = False # heals when unlocking the airstrike
AMMO_ON_GRANT = True # refills when unlocking the airstrike

HEAL_ON_LAUNCH = True # heals when calling in the airstrike
AMMO_ON_LAUNCH = False # refills when calling in the airstrike

S_READY = "Airstrike support ready! SCOPE and HOLD <V> (sneak) to launch"
S_FAILED = 'You need to aim your airstrike somewhere, not at the sky!'
S_NO_STREAK = 'Every {streak} kills in a row you unlock an ' \
    'airstrike. {remaining} kills to go!'
S_COOLDOWN = '{seconds} seconds before your team can launch another airstrike'
S_ALLIED = 'Ally {player} called in an airstrike on location {coords}'
S_ENEMY = '[WARNING] Enemy air support heading to {coords}!'
S_MOVED = 'You must hold still while targeting the airstrike'
S_STAND = 'You must be standing up to target the airstrike'

TEAM_COOLDOWN = 25.0 # seconds until another airstrike can be called
ZOOMV_TIME = 0.25 # seconds holding V until airstrike is called
ZOOMV_RAY_LENGTH = 192.0
ARRIVAL_DELAY = 1.2 # seconds from airstrike notice to arrival

@alias('a')
def airstrike(connection, *args):
    if connection not in connection.protocol.players:
        raise ValueError()
    player = connection
    
    if player.airstrike:
        return S_READY
    else:
        kills_left = STREAK_REQUIREMENT - player.airstrike_streak
        return S_NO_STREAK.format(streak = STREAK_REQUIREMENT,
            remaining = kills_left)

add(airstrike)

# debug
from commands import admin, name, get_player
@admin
@name('givestrike')
def give_strike(connection, player = None):
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()    
    player.airstrike = True
    custom_refill(player, HEAL_ON_GRANT, AMMO_ON_GRANT)
    player.send_chat(S_READY)
add(give_strike)

def bellrand(a, b):
    return (uniform(a, b) + uniform(a, b) + uniform(a, b)) / 3.0

class Nag(object):
    call = None
    
    def __init__(self, seconds, f, *args, **kw):
        self.seconds = seconds
        self.f = f
        self.args = args
        self.kw = kw
    
    def start_or_reset(self):
        if self.call and self.call.active():
            self.call.reset(ZOOMV_TIME)
        else:
            self.call = callLater(self.seconds, self.f, *self.args, **self.kw)
    
    def stop(self):
        if self.call and self.call.active():
            self.call.cancel()
        self.call = None
    
    def active(self):
        return self.call and self.call.active()
    
    def __del__(self):
        self.stop()

def custom_refill(player, heal, ammo):
    if heal or ammo:
        weapon = player.weapon_object
        old_stock = weapon.current_stock
        old_hp = player.hp
        player.refill()
        if not heal and old_hp != 100:
            set_hp.hp = old_hp
            set_hp.not_fall = 0
            set_hp.source_x = 0
            set_hp.source_y = 0
            set_hp.source_z = 0
            player.send_contained(set_hp)
            player.hp = old_hp
        if not ammo:
            weapon_reload.player_id = player.player_id
            weapon_reload.clip_ammo = weapon.current_ammo
            weapon_reload.reserve_ammo = old_stock

def apply_script(protocol, connection, config):
    class AirstrikeConnection(connection):
        airstrike = False
        airstrike_grenade_calls = None
        airstrike_streak = 0
        airstrike_nag = None
        zoomv = None
        zoomv_nag = None
        last_zoomv_message = None
        
        def start_airstrike(self, x, y, z):
            coords = to_coordinates(x, y)
            message = S_ALLIED.format(player = self.name, coords = coords)
            self.protocol.send_chat(message, global_message = False,
                team = self.team)
            message = S_ENEMY.format(coords = coords)
            self.protocol.send_chat(message, global_message = False,
                team = self.team.other)
            self.team.last_airstrike = seconds()
            
            callLater(ARRIVAL_DELAY, self.do_airstrike, x, y, z)
        
        def do_airstrike(self, x, y, z):
            if self.name is None:
                return
            direction = 1 if self.team.id == 0 else -1
            jitter = (3.0 * direction, 4.0 * direction) # forward randomization range
            spread = 0.6 # symmetric Y up and down
            radius = 30.0 # maximum reach from ground zero
            estimate_travel = 32 * z / 64 # to offset spawn coordinates
            x = max(0, min(511, x - estimate_travel * direction))
            grenade_z = 1
            
            self.airstrike_grenade_calls = []
            for i in xrange(10):
                angle = vonmisesvariate(0.0, 0.0) # fancy for uniform(0, 2*pi)
                distance = bellrand(-radius, radius)
                grenade_x = x + cos(angle) * distance
                grenade_y = y + sin(angle) * distance
                for j in xrange(5):
                    grenade_x += uniform(*jitter)
                    grenade_y += uniform(-spread, spread)
                    delay = i * 0.85 + j * 0.11
                    call = callLater(delay, self.create_airstrike_grenade,
                        grenade_x, grenade_y, grenade_z)
                    self.airstrike_grenade_calls.append(call)
        
        def create_airstrike_grenade(self, x, y, z):
            if self.name is None:
                return
            direction = 1 if self.team.id == 0 else -1
            z_speed = 3.5 # used to be 0.5
            
            position = Vertex3(x, y, z)
            velocity = Vertex3(direction, 0.0, z_speed)
            grenade = self.protocol.world.create_object(Grenade, 0.0,
                position, None, velocity, self.airstrike_exploded)
            grenade.name = 'airstrike'
            
            collision = grenade.get_next_collision(UPDATE_FREQUENCY)
            if not collision:
                return
            eta, x, y, z = collision
            grenade.fuse = eta
            grenade_packet.value = grenade.fuse
            grenade_packet.player_id = self.player_id
            grenade_packet.position = position.get()
            grenade_packet.velocity = velocity.get()
            self.protocol.send_contained(grenade_packet)
        
        def airstrike_exploded(self, grenade):
            grenade.velocity.normalize()
            penetration = 3 # go forward some extra distance until we collide
            while penetration:
                penetration -= 1
                grenade.position += grenade.velocity
                solid = self.protocol.map.get_solid(*grenade.position.get())
                if solid or solid is None:
                    break
            self.grenade_exploded(grenade)
        
        def end_airstrike(self):
            if self.airstrike_grenade_calls:
                for grenade_call in self.airstrike_grenade_calls:
                    if grenade_call and grenade_call.active():
                        grenade_call.cancel()
            self.airstrike_grenade_calls = None
        
        def start_zoomv(self):
            now = seconds()
            last_strike = getattr(self.team, 'last_airstrike', None)
            if last_strike is not None and now - last_strike < TEAM_COOLDOWN:
                remaining = ceil(TEAM_COOLDOWN - (seconds() - last_strike))
                message = S_COOLDOWN.format(seconds = int(remaining))
                self.send_zoomv_chat(message)
                return
            location = self.world_object.cast_ray(ZOOMV_RAY_LENGTH)
            if not location:
                self.send_zoomv_chat(S_FAILED)
                return
            self.zoomv.start_or_reset()
        
        def end_zoomv(self):
            location = self.world_object.cast_ray(ZOOMV_RAY_LENGTH)
            if not location:
                self.send_chat(S_FAILED)
                return
            self.airstrike = False
            self.airstrike_streak = 0
            self.start_airstrike(*location)
            custom_refill(self, HEAL_ON_LAUNCH, AMMO_ON_LAUNCH)
        
        def send_zoomv_chat(self, message):
            last_message = self.last_zoomv_message
            if last_message is None or seconds() - last_message >= 1.0:
                self.send_chat(message)
                self.last_zoomv_message = seconds()
        
        def on_team_changed(self, old_team):
            self.end_airstrike()
            connection.on_team_changed(self, old_team)
        
        def on_login(self, name):
            self.airstrike_nag = Nag(4.0, self.send_chat, S_READY)
            self.zoomv = Nag(1.0, self.end_zoomv)
            self.zoomv_nag = Nag(2.0, self.send_zoomv_chat, S_STAND)
            connection.on_login(self, name)
        
        def on_reset(self):
            self.airstrike = False
            self.airstrike_streak = 0
            self.airstrike_nag = None
            self.zoomv = None
            self.zoomv_nag = None
            self.end_airstrike()
            connection.on_reset(self)
        
        def on_spawn(self, location):
            if self.airstrike:
                self.airstrike_nag.start_or_reset()
            connection.on_spawn(self, location)
        
        def on_kill(self, killer, type, grenade):
            self.airstrike_streak = 0
            self.airstrike_nag.stop()
            self.zoomv.stop()
            if killer is not None and self.team is not killer.team:
                # no self-kills and no teamkills
                if grenade is None or grenade.name == 'grenade':
                    # only regular grenades count for streak
                    if not killer.airstrike:
                        # don't increase streak if we have a strike on-hold
                        killer.airstrike_streak += 1
                        if killer.airstrike_streak == STREAK_REQUIREMENT:
                            killer.airstrike = True
                            killer.send_chat(S_READY)
                            custom_refill(killer, HEAL_ON_GRANT, AMMO_ON_GRANT)
            connection.on_kill(self, killer, type, grenade)
        
        def on_shoot_set(self, fire):
            if self.tool == WEAPON_TOOL:
                if self.zoomv.active() and fire:
                    self.zoomv.start_or_reset()
                    self.send_zoomv_chat(S_MOVED)
            connection.on_shoot_set(self, fire)
        
        def on_walk_update(self, up, down, left, right):
            if self.zoomv.active() and (up or down or left or right):
                self.zoomv.start_or_reset()
                self.send_zoomv_chat(S_MOVED)
            return connection.on_walk_update(self, up, down, left, right)
        
        def on_secondary_fire_set(self, secondary):
            if self.airstrike and self.tool == WEAPON_TOOL:
                if secondary:
                    if self.world_object.crouch:
                        self.zoomv_nag.start_or_reset()
                else:
                    self.zoomv.stop()
                    self.zoomv_nag.stop()
            connection.on_secondary_fire_set(self, secondary)
        
        def on_animation_update(self, jump, crouch, sneak, sprint):
            obj = self.world_object
            secondary = obj.secondary_fire
            if self.airstrike and self.tool == WEAPON_TOOL and secondary:
                if sneak and not self.zoomv.active():
                    if obj.up or obj.down or obj.left or obj.right:
                        self.send_zoomv_chat(S_MOVED)
                        return
                    self.start_zoomv()
                elif not sneak and self.zoomv.active():
                    if crouch:
                        # crouching was the reason sneak got turned off
                        self.send_zoomv_chat(S_STAND)
                    self.zoomv.stop()
                elif crouch:
                    self.zoomv_nag.start_or_reset()
                elif not crouch:
                    self.zoomv_nag.stop()
            return connection.on_animation_update(self, jump, crouch, sneak,
                sprint)
    
    return protocol, AirstrikeConnection