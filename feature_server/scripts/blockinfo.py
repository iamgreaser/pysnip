"""
A tool for identifying griefers.

Maintainer: hompy
Blocks per player added by +RainbowDash
"""

from twisted.internet import reactor
from twisted.internet.reactor import seconds
from pyspades.collision import distance_3d_vector
from pyspades.common import prettify_timespan
from commands import add, admin, name, get_player, alias

# "blockinfo" must be AFTER "votekick" in the config.txt script list
AUTO_GC = True #Turns grief alert on or off
AUTO_GC_TIME = 2 #Default time for griefcheck in grief alert
AUTO_GC_BLOCKS = 40 #Number of blocks to begin warning at
AUTO_GC_MAPBLOCKS = 40 #Number of mapblocks to begin warning at
AUTO_GC_RATIO = .7 #ratio of teamblocks to enemy blocks to warn at
GRIEFCHECK_ON_VOTEKICK = False
IRC_ONLY = True

@name('griefcheck')
@alias('gc')
def grief_check(connection, player, time = None):
    player = get_player(connection.protocol, player)
    protocol = connection.protocol
    color = connection not in protocol.players and connection.colors
    minutes = float(time or 2)
    if minutes < 0.0:
        raise ValueError()
    time = seconds() - minutes * 60.0
    blocks_removed = player.blocks_removed or []
    blocks = [b[1] for b in blocks_removed if b[0] >= time]
    player_name = player.name
    if color:
        player_name = (('\x0303' if player.team.id else '\x0302') +
            player_name + '\x0f')
    message = '%s removed %s block%s in the last ' % (player_name,
        len(blocks) or 'no', '' if len(blocks) == 1 else 's')
    if minutes == 1.0:
        minutes_s = 'minute'
    else:
        minutes_s = '%s minutes' % ('%f' % minutes).rstrip('0').rstrip('.')
    message += minutes_s + '.'
    if len(blocks):
        infos = set(blocks)
        infos.discard(None)
        if color:
            names = [('\x0303' if team else '\x0302') + name for name, team in
                infos]
        else:
            names = set([name for name, team in infos])
        namecheck = [[name, team, 0] for name, team in infos]
        if len(names) > 0:
            for f in range(len(namecheck)):
                for i in range(len(blocks_removed)):
                    if blocks_removed[i][1] is not None:
                        if namecheck[f][0] == blocks_removed[i][1][0] and namecheck[f][1] == blocks_removed[i][1][1] and blocks_removed[i][0] >= time:
                            namecheck[f][2] += 1
             
            message += (' Some of them were placed by ')
            for i in range(len(names)):
                message += ('\x0f, ' if color else ', ') + names[i] + "(" + str(namecheck[i][2]) + ")"
            userblocks = 0
            for i in range(len(namecheck)):
                userblocks = userblocks + namecheck[i][2]
            if userblocks == len(blocks):
                pass
            else:
                message += ('\x0f. ' if color else '. ') + str(len(blocks) - userblocks) + " were map blocks"
            message += '\x0f.' if color else '.'
        else:
            message += ' All of them were map blocks.'
        last = blocks_removed[-1]
        time_s = prettify_timespan(seconds() - last[0], get_seconds = True)
        message += ' Last one was destroyed %s ago' % time_s
        whom = last[1]
        if whom is None and len(names) > 0:
            message += ', and was part of the map'
        elif whom is not None:
            name, team = whom
            if color:
                name = ('\x0303' if team else '\x0302') + name + '\x0f'
            message += ', and belonged to %s' % name
        message += '.'
    switch_sentence = False
    if player.last_switch is not None and player.last_switch >= time:
        time_s = prettify_timespan(seconds() - player.last_switch,
            get_seconds = True)
        message += ' %s joined %s team %s ago' % (player_name,
            player.team.name, time_s)
        switch_sentence = True
    teamkills = len([t for t in player.teamkill_times or [] if t >= time])
    if teamkills > 0:
        s = ', and killed' if switch_sentence else ' %s killed' % player_name
        message += s + ' %s teammates in the last %s' % (teamkills, minutes_s)
    if switch_sentence or teamkills > 0:
        message += '.'
    votekick = getattr(protocol, 'votekick', None)
    if (votekick and votekick.victim is player and
        votekick.victim.world_object and votekick.instigator.world_object):
        instigator = votekick.instigator
        tiles = int(distance_3d_vector(player.world_object.position,
            instigator.world_object.position))
        instigator_name = (('\x0303' if instigator.team.id else '\x0302') +
            instigator.name + '\x0f')
        message += (' %s is %d tiles away from %s, who started the votekick.' %
            (player_name, tiles, instigator_name))
    return message

add(grief_check)

def griefalert(self):
    for i in ['guard','moderator','admin']:
        if i in self.user_types:
            return
    player = self
    time = seconds() - AUTO_GC_TIME * 60
    blocks_removed = player.blocks_removed or []
    blocks = [b[1] for b in blocks_removed if b[0] >= time]
    player_name = player.name
    infos = set(blocks)
    infos.discard(None)
    namecheck = [[name, team, 0] for name, team in infos]
    if len(namecheck) > 0:
        for f in range(len(namecheck)):
            for i in range(len(blocks_removed)):
                if blocks_removed[i][1] is not None:
                    if namecheck[f][0] == blocks_removed[i][1][0] and namecheck[f][1] == blocks_removed[i][1][1] and blocks_removed[i][0] >= time:
                        namecheck[f][2] += 1
                    
    teamblocks = 0
    enemyblocks = 0
    mapblocks = 0
    for i in range(len(namecheck)):
        if namecheck[i][1] == player.team.id:
            teamblocks += namecheck[i][2]
        else:
            enemyblocks += namecheck[i][2]
    for i in range(len(blocks_removed)):
        if blocks_removed[i][1] is None and blocks_removed[i][0] >= time:
            if int(blocks_removed[i][2]) == 1 and int(player.team.id) == 1:
                mapblocks += 1
            elif int(blocks_removed[i][2]) == 0 and int(player.team.id) == 0:
                mapblocks += 1
           
    if not self.griefcheck_delay and float(teamblocks)/float(len(blocks)) >= AUTO_GC_RATIO and len(blocks) >= AUTO_GC_BLOCKS:
        message = "Potential griefer detected: " + player_name
        message += " removed " + str(len(blocks)) + " blocks in the past " + str(AUTO_GC_TIME) + " minutes, "
        message += " " + str(int(float(teamblocks)/float(len(blocks))* 100)) + "% from their own team"
        irc_relay = self.protocol.irc_relay 
	if irc_relay.factory.bot and irc_relay.factory.bot.colors:
            message = '\x0303* ' + message + '\x0f'
        self.griefcheck_delay = True
        reactor.callLater(10,griefcheckdelay,self)
	irc_relay.send(message)
    elif not self.griefcheck_delay and mapblocks >= AUTO_GC_MAPBLOCKS:
        message = "Potential griefer detected: " + player_name
        message += " removed " + str(mapblocks) + " map blocks on their side in the past " + str(AUTO_GC_TIME) + " minutes"
        irc_relay = self.protocol.irc_relay 
        if irc_relay.factory.bot and irc_relay.factory.bot.colors:
            message = '\x0303* ' + message + '\x0f'
        self.griefcheck_delay = True
        reactor.callLater(10,griefcheckdelay,self)
	irc_relay.send(message)

    
def griefcheckdelay(self):
    self.griefcheck_delay = False
    
def apply_script(protocol, connection, config):
    has_votekick = 'votekick' in config.get('scripts', [])
    
    class BlockInfoConnection(connection):
        blocks_removed = None
        teamkill_times = None
        griefcheck_delay = False
        
        def on_reset(self):
            self.blocks_removed = None
            self.teamkill_times = None
            connection.on_reset(self)
        
        def on_block_build(self, x, y, z):
            if self.protocol.block_info is None:
                self.protocol.block_info = {}
            self.protocol.block_info[(x, y, z)] = (self.name, self.team.id)
            connection.on_block_build(self, x, y, z)
        
        def on_line_build(self, points):
            if self.protocol.block_info is None:
                self.protocol.block_info = {}
            name_team = (self.name, self.team.id)
            for point in points:
                self.protocol.block_info[point] = name_team
            connection.on_line_build(self, points)
        
        def on_block_removed(self, x, y, z):
            if self.protocol.block_info is None:
                self.protocol.block_info = {}
            if self.blocks_removed is None:
                self.blocks_removed = []
            pos = (x, y, z)
            if pos[0] >= 256:
                side = 1
            else:
                side = 0                
            info = (seconds(), self.protocol.block_info.pop(pos, None),side)
            self.blocks_removed.append(info)
            if AUTO_GC:
                griefalert(self)
                
            connection.on_block_removed(self, x, y, z)
        
        def on_kill(self, killer, type, grenade):
            if killer and killer.team is self.team:
                if killer.teamkill_times is None:
                    killer.teamkill_times = []
                killer.teamkill_times.append(seconds())
            return connection.on_kill(self, killer, type, grenade)
    
    class BlockInfoProtocol(protocol):
        block_info = None
        
        def on_map_change(self, map):
            self.block_info = None
            protocol.on_map_change(self, map)
        
        def on_votekick_start(self, instigator, victim, reason):
            result = protocol.on_votekick_start(self, instigator, victim, reason)
            if result is None and GRIEFCHECK_ON_VOTEKICK:
                message = grief_check(instigator, victim.name)
                message2 = grief_check(instigator, victim.name,5)
                if IRC_ONLY:
                    self.irc_say('* ' + message)
                    self.irc_say('* ' + message2)
                else:
                    self.send_chat(message, irc = True)
            return result
    
    return BlockInfoProtocol, BlockInfoConnection
