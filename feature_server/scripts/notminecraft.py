"""
NotMinecraft: kills-based antigrief solution.

Author: GreaseMonkey (as usual, also stitched together from other sources)
"""

from pyspades.constants import *

NOTMINECRAFT_KILLS_FOR_BUILD = 5
NOTMINECRAFT_KILLS_FOR_BREAK = 5

def apply_script(protocol, connection, config):
    class NotMinecraftConnection(connection):
        notminecraft_kills = 0
        
        def notminecraft_check_kills(self, k):
            # NOTE: True on FAIL!
            p = True
            for i in ['admin', 'moderator', 'guard', 'trusted']:
                if i in self.user_types:
                    p = False
            if self.god:
                p = False

            if not p:
                if self.notminecraft_kills < k:
                    return True

            return False
        
        def on_kill(self, killer, type, grenade):
            if killer is not None and self.team is not killer.team:
                if self != killer:
                    killer.notminecraft_kills += 1
            return connection.on_kill(self, killer, type, grenade)
    
        def on_block_build_attempt(self, x, y, z):
            if self.notminecraft_check_kills(NOTMINECRAFT_KILLS_FOR_BUILD):
                # note, being deliberately vague to stop griefers being cheeky --GM
                self.send_chat('You do not have enough kills to build blocks!')
                return False
            return connection.on_block_build_attempt(self, x, y, z)

        def on_line_build_attempt(self, points):
            if self.notminecraft_check_kills(NOTMINECRAFT_KILLS_FOR_BUILD):
                self.send_chat('You do not have enough kills to build blocks!')
                return False
            return connection.on_line_build_attempt(self, points)
        
        def on_block_destroy(self, x, y, z, mode):
            if self.notminecraft_check_kills(NOTMINECRAFT_KILLS_FOR_BREAK):
                if self.tool is SPADE_TOOL:
                    self.send_chat('You do not have enough kills to break blocks!')
                return False
            return connection.on_block_destroy(self, x, y, z, mode)
    
    class NotMinecraftProtocol(protocol):
        pass
            
    return NotMinecraftProtocol, NotMinecraftConnection
