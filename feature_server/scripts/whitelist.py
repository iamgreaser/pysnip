"""
Allows for a whitelist over the top of range bans

Author: GreaseMonkey

Public Domain
"""
import json
import commands
from networkdict import NetworkDict
from pyspades.constants import *
@commands.admin
def wladd(connection, ip, notes):
    return connection.protocol.wl_add(connection, ip, notes)
commands.add(wladd)

@commands.admin
def wldel(connection, ip):
    return connection.protocol.wl_del(connection, ip)
commands.add(wldel)

@commands.admin
def wlget(connection, ip):
    return connection.protocol.wl_get(connection, ip)
commands.add(wlget)

# It also slices toast!
@commands.admin
def togglesmg(connection):
    protocol = connection.protocol
    protocol.smg_banned = not protocol.smg_banned
    status = "disabled" if protocol.smg_banned else "enabled"
    if protocol.smg_banned:
        for pv in protocol.players:
            p = protocol.players[pv]
            if p.weapon == SMG_WEAPON:
                p.send_chat("SMG disabled - weapon changed to rifle.")
                p.set_weapon(RIFLE_WEAPON, False, False)
    
    if hasattr(connection, 'send_chat'):
        connection.send_chat("SMG is now %s" % status)
    protocol.irc_say("SMG %s by %s" % (status, connection.name))
commands.add(togglesmg)

def apply_script(protocol, connection, config):
    class WhitelistProtocol(protocol):
        def __build_dictwrapper(self, wrapped, wlcall):
            class NetworkDictWrapper:
                def __getattr__(self, *args, **kwargs):
                    return getattr(wrapped, *args, **kwargs)
                
                def __setattr__(self, *args, **kwargs):
                    return setattr(wrapped, *args, **kwargs)
                
                def __getitem__(self, ip):
                    if wlcall(ip):
                        raise KeyError()
                    else:
                        return wrapped[ip]
            return NetworkDictWrapper()
        
        whitelist_ips = {}
        smg_banned = False
        
    	def __init__(self, *args, **kwargs):
    	    ret = protocol.__init__(self, *args, **kwargs)
    	    self.wl_load()
    	    self.bans = self.__build_dictwrapper(self.bans, self.wl_is_listed)
        
    	def wl_is_listed(self, ip):
            return self.whitelist_ips[ip] if (ip in self.whitelist_ips) else None
        
        def wl_get(self, connection, ip):
            if self.wl_is_listed(ip):
                notes = self.whitelist_ips[ip]
                return "Notes for %s: %s" % (ip, notes)
            else:
                return "IP %s not whitelisted" % ip
        
        def wl_add(self, connection, ip, notes):
            if self.wl_is_listed(ip):
                oldnotes = self.whitelist_ips[ip]
                self.whitelist_ips[ip] = notes
                self.irc_say("IP %s updated on the whitelist by %s: %s" % (ip, connection.name, notes))
                self.irc_say("Original notes: %s" % oldnotes)
                if hasattr(connection, 'send_chat'):
                    connection.send_chat("IP %s updated on the whitelist: %s" % (ip, notes))
                    connection.send_chat("Original notes: %s" % oldnotes)
            else:
                self.whitelist_ips[ip] = notes
                if hasattr(connection, 'send_chat'):
                    connection.send_chat("IP %s added to whitelist: %s" % (ip, notes))
                self.irc_say("IP %s added to whitelist by %s: %s" % (ip, connection.name, notes))
            return self.wl_save()
        
        def wl_del(self, connection, ip):
            if self.wl_is_listed(ip):
            	del self.whitelist_ips[ip]
                if hasattr(connection, 'send_chat'):
                    connection.send_chat("IP %s deleted from whitelist" % ip)
                self.irc_say("IP %s deleted from whitelist by %s" % (ip, connection.name))
                return self.wl_save()
            else:
                return "IP %s not whitelisted" % ip
        
        def wl_load(self):
            fp = None
            try:
                fp = open("whitelist_ips.txt","r")
                try:
                    self.whitelist_ips = json.load(fp)
                    fp.close()
                except ValueError:
                    print "ValueError loading whitelist, generating new one!"
                    self.whitelist_ips = {}
                    self.wl_save()
            except IOError:
                print "IOError loading whitelist, generating new one!"
                self.whitelist_ips = {}
                self.wl_save()
        
        def wl_save(self):
            fp = open("whitelist_ips.txt","w")
            json.dump(self.whitelist_ips, fp)
            fp.close()
    
    class WhitelistConnection(connection):
    	def __init__(self, *args, **kwargs):
    	    return connection.__init__(self, *args, **kwargs)
    	
        def on_weapon_set(self, wpnid):
            if self.protocol.smg_banned and wpnid == SMG_WEAPON:
                self.send_chat("SMG is disabled")
                return False
            return connection.on_weapon_set(self, wpnid)
        
        def set_weapon(self, weapon, local = False, no_kill = False, *args, **kwargs):
            if self.protocol.smg_banned and weapon == SMG_WEAPON:
                self.send_chat("SMG is disabled, rifle given instead")
                weapon = RIFLE_WEAPON
                if local:
	                no_kill = True
	                local = False
            return connection.set_weapon(self, weapon, local, no_kill, *args, **kwargs)
    
    return WhitelistProtocol, WhitelistConnection