"""
Blocks are twice as hard to break with the SMG.
"""

from pyspades.common import make_color
from pyspades.constants import *
from pyspades.server import block_action, set_color


def rebuild_block(player, x, y, z, color):
    set_color.value = make_color(*color)
    set_color.player_id = 32
    block_action.player_id = 32
    block_action.x = x
    block_action.y = y
    block_action.z = z
    block_action.value = DESTROY_BLOCK
    player.send_contained(block_action)
    block_action.value = BUILD_BLOCK
    player.send_contained(set_color)
    player.send_contained(block_action)

def apply_script(protocol, connection, config):
    class SMGBlockConnection(connection):
        def on_block_destroy(self, x, y, z, value):
            can_destroy = connection.on_block_destroy(self, x, y, z, value)
            if can_destroy != False and self.weapon == SMG_WEAPON self.tool == WEAPON_TOOL and (
                    (x, y, z) not in self.protocol.smg_blocks or
                    self.protocol.smg_blocks[(x, y, z)] is None):
                self.protocol.smg_blocks[(x, y, z)] = True
                if self.protocol.map.get_color(x, y, z) is not None:
                    rebuild_block(self, x, y, z, self.protocol.map.get_color(x, y, z))
                return False
            elif ((x, y, z) in self.protocol.smg_blocks and
                    self.protocol.smg_blocks[(x, y, z)] is not None):
                self.protocol.smg_blocks[(x, y, z)] = None
            return can_destroy
    
    class SMGBlockProtocol(protocol):
        smg_blocks = None
        
        def on_map_change(self, map):
            self.smg_blocks = {}
            protocol.on_map_change(self, map)
    
    return SMGBlockProtocol, SMGBlockConnection
