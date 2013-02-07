"""
RainbowDash admin bot, includes code from autohelp.py and others.
Togglesmg from GreaseMonkey's whitelist script,
togglespade based off nogunall from hacktools.py
Adds /masterrefresh which will refresh the master connection every 30 min.
/togglesmg
/toggleshotty
/togglesemi
/togglespade
/noscope
/togglenade
/togglecaps

Modified by GreaseMonkey for cleanliness.
Also, soft tabs suck.
"""

from twisted.internet import reactor
import re
from commands import add, admin, name, get_player, alias
import commands
from blockinfo import grief_check
from aimbot2 import hackinfo
from pyspades.constants import *
from pyspades import contained as loaders

REFRESH_MASTER = True
WEAPON_TOGGLE = True
GRIEFCHECK_ON_VOTEKICK = True
HACKCHECK_ON_VOTEKICK = True
RACISM_BAN_LENGTH = 1440

WPN_NAME_LIST = {
	RIFLE_WEAPON: "Rifle",
	SMG_WEAPON: "SMG",
	SHOTGUN_WEAPON: "Shotgun",
}

WPN_SHORTCUT_LIST = {
	RIFLE_WEAPON: "semi",
	SMG_WEAPON: "smg",
	SHOTGUN_WEAPON: "shotty",
}

offenders = []
masterisrunning = 1
weapon_reload = loaders.WeaponReload()
badwords = re.compile(".*(fuck|shit|bitch|cunt|cocksucker|nigg(er|a)|penis|admin).*", re.IGNORECASE)
slurpat = re.compile(".*(nigg(er|a|3r)|niqq(er|a|3r)).*", re.IGNORECASE)
griefpat = re.compile(".*(gr.*f.*(ing|er)|grief|destroy|gief|geif|giraf).*", re.IGNORECASE)
aimbotpat = re.compile(".*(aim|bot|ha(ck|x)|cheat|h4x|hex|hacer).*", re.IGNORECASE)
def slur_match(player, msg):
	return (not slurpat.match(msg) is None)
def name_match(player):
	return (not badwords.match(player.name) is None)
def name_empty(player):
	if (player.name == " ") or (player.name == ""):
		return True
	else:
		return False
def grief_match(reason):
	return (not griefpat.match(reason) is None)
def hack_match(reason):
	return (not aimbotpat.match(reason) is None)
def fill_weapon(player):
	weapon = player.weapon_object
	weapon.set_shoot(True)
	weapon.current_ammo = player.bulletcount
	weapon_reload.player_id = player.player_id
	weapon_reload.clip_ammo = weapon.current_ammo
	weapon_reload.reserve_ammo = weapon.current_stock
	player.send_contained(weapon_reload)
def empty_weapon(player):
	weapon = player.weapon_object
	weapon.set_shoot(False)
	player.bulletcount = weapon.current_ammo
	weapon.current_ammo = 0
	weapon_reload.player_id = player.player_id
	weapon_reload.clip_ammo = weapon.current_ammo
	weapon_reload.reserve_ammo = weapon.current_stock
	player.send_contained(weapon_reload)
def empty_weapon_full(player):
	weapon = player.weapon_object
	weapon.set_shoot(False)
	weapon.current_ammo = 0
	weapon.current_stock = 0
	weapon_reload.player_id = player.player_id
	weapon_reload.clip_ammo = weapon.current_ammo
	weapon_reload.reserve_ammo = weapon.current_stock
	player.send_contained(weapon_reload)
@admin
def status(self):
        if hasattr(self, 'send_chat'):
                
		self.send_chat("--Server status--\n Rifle: %s\n SMG: %s\n Shotty: %s\n Grenades: %s\n Noscope: %s\n Spade War: %s" % (self.protocol.wpn_banned[RIFLE_WEAPON],self.protocol.wpn_banned[SMG_WEAPON],self.protocol.wpn_banned[SHOTGUN_WEAPON],self.protocol.nade_banned,self.protocol.noscope,self.protocol.spade_only))
	else:
		self.protocol.irc_say("--Server status--\n Rifle: %s\n SMG: %s\n Shotty: %s\n Grenades: %s\n Noscope: %s\n Spade War: %s" % (self.protocol.wpn_banned[RIFLE_WEAPON],self.protocol.wpn_banned[SMG_WEAPON],self.protocol.wpn_banned[SHOTGUN_WEAPON],self.protocol.nade_banned,self.protocol.noscope,self.protocol.spade_only))
add(status)
@admin
def noscope(connection):
	protocol = connection.protocol
	protocol.noscope = not protocol.noscope
	if protocol.noscope:
		message = "Server is now noscopes only! If you use your scope, you will run out of ammo!"
	else:
		message = "Server is back to normal, snipe away!"
	protocol.send_chat(message, irc = True)
add(noscope)

@admin
def masterrefresh(self):
	global masterisrunning
	if not REFRESH_MASTER:
		if hasattr(self, 'send_chat'):
			self.send_chat("Command not enabled")
		else:
			self.protocol.irc_say("Command not enabled")
		return
	elif not masterisrunning:
		masterisrunning = 1
		if hasattr(self, 'send_chat'):
			self.send_chat("Master will now be refreshed every 30 min.")
		else:
			self.protocol.irc_say("Master will now be refreshed every 30 min.")
		masterloop(self)
	else:
		masterisrunning = 0
		if hasattr(self, 'send_chat'):
			self.send_chat("Master refresh is now off.")
		else:
			self.protocol.irc_say("Master refresh is now off.")
		return
add(masterrefresh)

def masterloop(self):
	if REFRESH_MASTER and masterisrunning:
		protocol = self.protocol
		protocol.set_master_state(not protocol.master)
		protocol.set_master_state(not protocol.master)
		protocol.irc_say("Master was toggled")
		reactor.callLater(1800,masterloop,self)
@admin
def togglecaps(connection, player = None):
        protocol = connection.protocol
        if player is not None:
                player = get_player(protocol, player)
        elif connection in protocol.players:
                player = connection
        else:
                raise ValueError()
        
        player.no_caps = not player.no_caps
        status = "no longer" if player.no_caps else "now"
        protocol.irc_say("%s can %s use caps" % (player.name, status))
add(togglecaps)

@admin
def togglenade(connection):
	protocol = connection.protocol
	protocol.nade_banned = not protocol.nade_banned
	if protocol.nade_banned:
		message = "%s disabled grenades!" % (connection.name)
		for player in protocol.players.itervalues():
			player.grenades = 0			
	else:
		message = "Grenades are enabled"
                for player in protocol.players.itervalues():
			player.grenades = 3
	protocol.send_chat(message, irc = True)
add(togglenade)

@admin
def togglespade(connection):
	protocol = connection.protocol
	protocol.spade_only = not protocol.spade_only
	if protocol.spade_only:
		message = "%s incited a melee rampage!" % (connection.name)
		for player in protocol.players.itervalues():
			empty_weapon_full(player)
	else:
		message = "Melee rampage is over, snipe away!"
		for player in protocol.players.itervalues():
			player.refill()
	protocol.send_chat(message, irc = True)
add(togglespade)


def add_toggle_wpn(weapon_token):
	banned_name = WPN_SHORTCUT_LIST[weapon_token]
	weapon_name = WPN_NAME_LIST[weapon_token]
	@admin
	def _f1(connection):
		protocol = connection.protocol
		protocol.wpn_banned[weapon_token] = not protocol.wpn_banned[weapon_token]
		if protocol.wpn_banned[RIFLE_WEAPON] and protocol.wpn_banned[SMG_WEAPON] and protocol.wpn_banned[SHOTGUN_WEAPON]:
			if hasattr(connection, 'send_chat'):
				connection.send_chat("Cannot disable all weapons")
			protocol.irc_say("Cannot disable all weapons")
			protocol.wpn_banned[weapon_token] = False
			return
		status = "disabled" if protocol.wpn_banned[weapon_token] else "enabled"
		if protocol.wpn_banned[weapon_token]:
			for pv in protocol.players:
				p = protocol.players[pv]
				if p.weapon == weapon_token:
					if not protocol.wpn_banned[RIFLE_WEAPON]:
						weapon = RIFLE_WEAPON
					elif not protocol.wpn_banned[SHOTGUN_WEAPON]:
						weapon = SHOTGUN_WEAPON
					else:
						weapon = SMG_WEAPON
					p.send_chat("%s disabled - weapon changed" % weapon_name)
					p.set_weapon(weapon, False, False)
		
		if hasattr(connection, 'send_chat'):
			connection.send_chat("%s is now %s" % (weapon_name, status))
		protocol.irc_say("%s %s by %s" % (weapon_name, status, connection.name))
	
	return name("toggle%s" % banned_name)(_f1)

for wpn in [RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON]:
        if WEAPON_TOGGLE:
                add(add_toggle_wpn(wpn))
        

def apply_script(protocol, connection, config):
	protocol.wpn_banned = {
		RIFLE_WEAPON: False,
		SMG_WEAPON: False,
		SHOTGUN_WEAPON: False,
	}
	protocol.noscope = False
	protocol.spade_only = False
	protocol.nade_banned = False
	protocol.racist = []
	protocol.muted = []
	connection.no_caps = False

	def unmuteracist(connection):
		connection.mute = False
		message = '%s has been unmuted.' % (connection.name)
		protocol.muted.pop()
		connection.protocol.send_chat(message, irc = True)
		
	def slurpunish(connection, reason = "Racist"):
		if not connection.address[0] in protocol.racist:
			protocol.racist[:0] = [connection.address[0]]
			protocol.muted[:0] = [connection.address[0]]
			connection.mute = True
			message = '%s has been muted for Racism. Next offence will result in a ban' % (connection.name)
			connection.protocol.send_chat(message, irc = True)
			reactor.callLater(300.0,unmuteracist,connection)
		else:
			connection.ban("Autoban: Repeat Racist", RACISM_BAN_LENGTH)
	def checkname(self):
		if name_match(self) or name_empty(self):
			for i in range(10):
				self.send_chat("Please change your name")
			reactor.callLater(5.0,namepunish,self)
			
	def namepunish(connection):
		connection.kick("Please get a new name")

	class AdminbotConnection(connection):
		def on_secondary_fire_set(self, secondary):
			if self.tool == WEAPON_TOOL:
				if secondary:
					if self.protocol.noscope:
						self.send_chat("You can't kill people while scoped in!")
						empty_weapon(self)
				else:
					if self.protocol.noscope:
						reactor.callLater(1,fill_weapon,self)
				
			return connection.on_secondary_fire_set(self, secondary)
                def on_grenade(self, time_left):
                        if self.protocol.nade_banned:    
                                pass
                        else:
                                return connection.on_grenade(self,time_left)
		def on_refill(self):
                        if self.protocol.nade_banned:
                                self.grenades = 0
			if self.protocol.spade_only:
				reactor.callLater(.1,empty_weapon_full,self)
			return connection.on_refill(self)
		def on_shoot_set(self, fire):
			if self.protocol.spade_only:
				reactor.callLater(.1,empty_weapon_full,self)
			return connection.on_shoot_set(self, fire)
		def on_spawn(self, pos):
                        if self.protocol.nade_banned:
                                self.grenades = 0
			if self.protocol.spade_only:
				reactor.callLater(.1,empty_weapon_full,self)
			return connection.on_spawn(self, pos)
		def on_chat(self, value, global_message):
                        if self.no_caps:
                                value = value.lower()
			if slur_match(self, value):
				reactor.callLater(0.0, slurpunish, self)
			return connection.on_chat(self, value, global_message)
		def on_team_join(self, team):
			 reactor.callLater(0.5,checkname,self)
			 if self.address[0] in self.protocol.muted:
				 self.mute = True
		def on_weapon_set(self, wpnid):
			if self.protocol.wpn_banned[wpnid]:
				self.send_chat("%s is disabled" % WPN_NAME_LIST[wpnid])
				return False
			return connection.on_weapon_set(self, wpnid)
	
		def set_weapon(self, weapon, local = False, no_kill = False, *args, **kwargs):
			if self.protocol.wpn_banned[weapon]:
				self.send_chat("%s is disabled" % WPN_NAME_LIST[weapon])
				if not self.protocol.wpn_banned[RIFLE_WEAPON]:
					weapon = RIFLE_WEAPON
				elif not self.protocol.wpn_banned[SHOTGUN_WEAPON]:
					weapon = SHOTGUN_WEAPON
				else:
					weapon = SMG_WEAPON
				if local:
					no_kill = True
					local = False
			return connection.set_weapon(self, weapon, local, no_kill, *args, **kwargs)
	class AdminbotProtocol(protocol):
		def on_votekick_start(self, instigator, victim, reason):
			result = protocol.on_votekick_start(self, instigator, victim, reason)
			if result is None and GRIEFCHECK_ON_VOTEKICK and grief_match(reason):
				message = grief_check(instigator, victim.name)
				message2 = grief_check(instigator, victim.name,5)
				#irc_relay = instigator.protocol.irc_relay 
				#if irc_relay.factory.bot and irc_relay.factory.bot.colors:
				#	message = '\x02* ' + message + '\x02'
				#	message2 = '\x02* ' + message2 + '\x02'
				#irc_relay.send(message)
				#irc_relay.send(message2)
				#self.irc_say(grief_check(instigator, victim.name))
				#self.irc_say(grief_check(instigator, victim.name,5))
			if result is None and HACKCHECK_ON_VOTEKICK and hack_match(reason):
				message = hackinfo(instigator, victim.name)
				irc_relay = instigator.protocol.irc_relay 
				if irc_relay.factory.bot and irc_relay.factory.bot.colors:
					message = '\x0304* ' + message + '\x0f'
				irc_relay.send(message)

			return result
		
	return AdminbotProtocol, AdminbotConnection
