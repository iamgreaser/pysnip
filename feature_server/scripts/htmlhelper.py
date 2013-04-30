from pyspades.collision import distance_3d_vector
from pyspades.common import prettify_timespan
from twisted.internet import reactor
from pyspades.common import prettify_timespan

def apply_script(protocol, connection, config):
    class HtmlHelperProtocol(protocol):
        def html_get_ratio(ignore, player):
            return player.ratio_kills/float(max(1,player.ratio_deaths))

        def html_get_aimbot2_rfl(ignore, player):
            if player.rifle_count != 0:
                return str(int(100.0 * (float(player.rifle_hits)/float(player.rifle_count)))) + '%'
            else:
                return 'None'
        def html_get_aimbot2_smg(ignore, player):
            if player.smg_count != 0:
                return str(int(100.0 * (float(player.smg_hits)/float(player.smg_count)))) + '%'
            else:
                return 'None'
        def html_get_aimbot2_sht(ignore, player):
            if player.shotgun_count != 0:
                return str(int(100.0 * (float(player.shotgun_hits)/float(player.shotgun_count)))) + '%'
            else:
                return 'None'

        def html_get_afk(ignore, player):
            return prettify_timespan(reactor.seconds() - player.last_activity, True)

        def html_grief_check(ignore, player, time):
            minutes = float(time or 2)
            if minutes < 0.0:
                raise ValueError()
            time = seconds() - minutes * 60.0
            blocks_removed = player.blocks_removed or []
            blocks = [b[1] for b in blocks_removed if b[0] >= time]
            player_name = player.name
            player_name = ('<font color="' + ('#007700' if player.team.id else '#000077') +
                '">' + player_name + '</font>')
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
                names = ['<font color="' + ('#007700' if team else '#000077') + '">'+ name for name, team in
                    infos]
                namecheck = [[name, team, 0] for name, team in infos]
                if len(names) > 0:
                    for f in range(len(namecheck)):
                        for i in range(len(blocks_removed)):
                            if blocks_removed[i][1] is not None:
                                if namecheck[f][0] == blocks_removed[i][1][0] and namecheck[f][1] == blocks_removed[i][1][1] and blocks_removed[i][0] >= time:
                                    namecheck[f][2] += 1
                     
                    message += (' Some of them were placed by ')
                    for i in range(len(names)):
                        message += ', ' + names[i] + "(" + str(namecheck[i][2]) + ")"
                    userblocks = 0
                    for i in range(len(namecheck)):
                        userblocks = userblocks + namecheck[i][2]
                    if userblocks == len(blocks):
                        pass
                    else:
                        message += '. ' + str(len(blocks) - userblocks) + " were map blocks"
                    message += '.'
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
                    name = '<font color="' + ('#007700' if team else '#000077') + '">' + name + '</font>'
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
                instigator_name = ('<font color="' + ('#007700' if instigator.team.id else '#000077') +
                    '">' + instigator.name + '</font>')
                message += (' %s is %d tiles away from %s, who started the votekick.' %
                    (player_name, tiles, instigator_name))
            return message

    return HtmlHelperProtocol, connection
