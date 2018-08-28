"""
MALSA 0.76: Make AoS Less Shit Again
Instantly turns a 0.75 server into a 0.76 server.
Version 3

Author: GreaseMonkey

Changelog:
Version 3: 2018-08-28
- Added piqueserver support.

Version 2: 2018-08-27
- Added damage falloff.

Version 1: 2018-08-26
- Initial release.
"""

# vim: set sts=4 sw=4 et :

import math
import zlib

import pyspades.constants
from pyspades.constants import TORSO, HEAD, ARMS, LEGS

import pyspades.collision
import pyspades.contained
import pyspades.master
import pyspades.server
import pyspades.weapon

class MalsaWorldUpdate(object):
    def __init__(self):
        self.items = None

    def write(self, data):
        data.writeByte(int(pyspades.contained.WorldUpdate.id))
        for (idx, item,) in enumerate(self.items):
            if not all(map(lambda vec: all(map(lambda el: el == 0.0, vec)),
                    item)):
                data.writeByte(idx)
                for vec in item:
                    for el in vec:
                        data.writeFloat(el, False)

class MalsaMapStart(object):
    def __init__(self):
        self.size = None
        self.crc = None
        self.map_name = None

    def write(self, data):
        data.writeByte(int(pyspades.contained.MapStart.id))
        data.writeInt(self.size, True, False)
        # TODO: get CRC
        #data.writeInt(self.crc, True, False)
        #data.writeString(self.map_name)

def apply_system_patches():
    #
    # Weapon changes
    #

    # Rifle
    pyspades.weapon.Rifle.delay = 0.6
    pyspades.weapon.Rifle.ammo = 8
    pyspades.weapon.Rifle.stock = 48
    pyspades.weapon.Rifle.reload_time = 2.5
    pyspades.weapon.Rifle.slow_reload = False
    pyspades.weapon.Rifle.damage[TORSO] = 60
    pyspades.weapon.Rifle.damage[HEAD] = 250
    pyspades.weapon.Rifle.damage[ARMS] = 50
    pyspades.weapon.Rifle.damage[LEGS] = 50

    # SMG
    # Delay: Vanilla uses 0.1 explicitly but in practice gets 0.112.
    # OpenSpades uses 0.11 explicitly.
    pyspades.weapon.SMG.delay = 0.11
    pyspades.weapon.SMG.ammo = 30
    pyspades.weapon.SMG.stock = 150
    pyspades.weapon.SMG.reload_time = 2.5
    pyspades.weapon.SMG.slow_reload = False
    pyspades.weapon.SMG.damage[TORSO] = 40
    pyspades.weapon.SMG.damage[HEAD] = 60
    pyspades.weapon.SMG.damage[ARMS] = 20
    pyspades.weapon.SMG.damage[LEGS] = 20

    # Shotgun
    pyspades.weapon.Shotgun.delay = 0.8
    pyspades.weapon.Shotgun.ammo = 8
    pyspades.weapon.Shotgun.stock = 48
    pyspades.weapon.Shotgun.reload_time = 0.4
    pyspades.weapon.Shotgun.slow_reload = True
    pyspades.weapon.Shotgun.damage[TORSO] = 40
    pyspades.weapon.Shotgun.damage[HEAD] = 60
    pyspades.weapon.Shotgun.damage[ARMS] = 20
    pyspades.weapon.Shotgun.damage[LEGS] = 20

    # Damage falloff
    def get_damage(self, value, position1, position2):
        falloff = 1 - ((pyspades.collision.distance_3d_vector(position1, position2)**1.5)*0.0004)
        return math.ceil(self.damage[value] * falloff)
    pyspades.weapon.BaseWeapon.get_damage = get_damage
    pyspades.weapon.Rifle.get_damage = get_damage
    pyspades.weapon.SMG.get_damage = get_damage
    pyspades.weapon.Shotgun.get_damage = get_damage

    #
    # Master server
    #
    pyspades.master.STAGING = 1
    pyspades.master.PORT = 32885

def apply_script(protocol, connection, config):
    malsa_world_update = MalsaWorldUpdate()
    malsa_map_start = MalsaMapStart()

    #
    # Connection
    #
    class MalsaConnection(connection):
        def send_map(self, data = None, *args, **kwargs):
            if data is not None:
                self.map_data = data
                try:
                    pyspades.server.map_start.size = data.get_size()
                except AttributeError:
                    import pyspades.player as player
                    player.map_start.size = data.get_size()
                    malsa_map_start.size = player.map_start.size
                else:
                    malsa_map_start.size = pyspades.server.map_start.size
                # TODO: get CRC
                #malsa_map_start.crc = zlib.crc32(self.protocol.map_info.data) & 0xFFFFFFFF
                #malsa_map_start.map_name = self.protocol.map_info.rot_info.get_map_name()
                self.send_contained(malsa_map_start)
                data = None
            elif self.map_data is None:
                return

            return connection.send_map(self, data, *args, **kwargs)


    #
    # Protocol
    #
    class MalsaProtocol(protocol):
        version = 4

        def send_contained(self, contained, *args, **kwargs):
            if contained == pyspades.server.world_update:
                #print("Wrap %s somehow" % (repr(dest_data),))
                malsa_world_update.items = contained.items
                contained = malsa_world_update
            else:
                #print("Class: %s" % (repr(contained.__class__.__name__),))
                pass

            return protocol.send_contained(self, contained, *args, **kwargs)

    #
    # We are done.
    #
    return MalsaProtocol, MalsaConnection

#
# Apply system patches immediately.
#
apply_system_patches()

