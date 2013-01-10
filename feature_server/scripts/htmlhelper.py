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
            color = False
            minutes = float(time or 2)
            if minutes < 0.0:
                raise ValueError()
            time = reactor.seconds() - minutes * 60.0
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
                if len(names) > 0:
                    message += (' Some of them were placed by ' +
                        ('\x0f, ' if color else ', ').join(names))
                    message += '\x0f.' if color else '.'
                else:
                    message += ' All of them were map blocks.'
                last = blocks_removed[-1]
                time_s = prettify_timespan(reactor.seconds() - last[0], get_seconds = True)
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
                time_s = prettify_timespan(reactor.seconds() - player.last_switch,
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
            return message
    return HtmlHelperProtocol, connection