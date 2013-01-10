"""
Checks if an IP is banned
Works with external bans too, but doesn't list their origin
"""

from commands import name, admin, add
from twisted.internet import reactor
from pyspades.common import prettify_timespan
@name('check')
@admin
def check_for_ban(connection, value):
    ban = connection.protocol.check_ban(value)
    if ban is not None:
        name, reason, time = None, None, None
        try:
            name, reason, time = ban
        except ValueError:
            reason = ban    
            
        ip = value
        #IP found in local ban list
        if name is not None:
            if time is not None:
                time =  prettify_timespan(time - reactor.seconds())
                ban_time = "Banned for %s" %(time)
            else:
                ban_time = "Permabanned"
            message = "%s found. %s for %s under the name %s" %(ip, ban_time, reason, name)
        #IP found in external
        else:
            message = "%s found on external ban list. Banned for %s" %(ip, reason)
        return message
    else:
        return "%s not found" %(value)

add(check_for_ban)

def apply_script(protocol, connection, config):

    class ExtraCommands(protocol):
        def check_ban(self, ip):
            #checks normal ban list first
            if ip in self.bans:
                ban = self.bans[ip]
                try:
                    name, reason, time = ban
                except:
                    name, reason = ban
                    time = None
                return name, reason, time
            else:
                #checks external ban lists
                manager = self.ban_manager
                reason = manager.get_ban(ip)
                if reason is not None:
                    name = None
                    time = None
                    return name, reason, time
            return None
            
    return ExtraCommands, connection