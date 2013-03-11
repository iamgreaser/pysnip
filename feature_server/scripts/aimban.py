from twisted.internet.reactor import seconds
from pyspades.server import position_data
from pyspades.constants import *
from commands import name, get_player, add, admin, alias
import operator
from math import acos, degrees, sqrt

angle_threshold = 10
update_threshold = 4
delay = 1

@name('settheta')
@admin
def settheta(connection, value = ''):
	protocol = connection.protocol
	try:
		angle_threshold = int(value)
	except ValueError:
		angle_threshold = 10
	message = 'Angle Threshold is now %d.' % angle_threshold
	connection.send_chat(message)
	protocol.irc_say(message)
add(settheta)

@name('setupdate')
@admin
def setupdate(connection, value = ''):
	protocol = connection.protocol
	try:
		update_threshold = int(value)
	except ValueError:
		update_threshold = 4
	message = 'Update Threshold is now %d.' % update_threshold
	connection.send_chat(message)
	protocol.irc_say(message)
add(setupdate)

@name('setdelay')
@admin
def setdelay(connection, value = ''):
	protocol = connection.protocol
	try:
		delay = int(value)
	except ValueError:
		delay = 1
	message = 'Delay is now %d.' % delay
	connection.send_chat(message)
	protocol.irc_say(message)
add(setdelay)

def apply_script(protocol, connection, config):
	class aimbanConnection(connection):
		update_count = 0
		previous_update_time = seconds()
		previous_hit_vector = (0, -1, 0) #North
		previous_hit_amount = 0
		
		def vector_angle(self, vec1, vec2):
			a = self.distance((0, 0, 0), vec1)
			b = self.distance((0, 0, 0), vec2)
			c = self.distance(vec1, vec2)
			cosc = (a **2 + b ** 2 - c ** 2) / (2 * a * b)
			if cosc < -1:
				cosc  = -1
			elif cosc > 1:
				cosc = 1
			data = acos(cosc) 
			return degrees(data)
			
		def distance(self, pos1, pos2):
			c = (pos1[0] - pos2[0]) **2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2
			return sqrt(c)
		
		def on_orientation_update(self, x, y, z):
			self.current_update_time = seconds()
			
			if self.current_update_time - self.previous_update_time >= delay:
				self.update_count = 0
				self.previous_hit_vector = (self.world_object.orientation.x * 10, self.world_object.orientation.y * 10, self.world_object.orientation.z * 10)
				
			self.update_count += 1
			self.previous_update_time = self.current_update_time
			return connection.on_orientation_update(self, x, y, z)
			
		def on_hit(self, hit_amount, hit_player, type, grenade):
			protocol = self.protocol
			if not grenade and self.tool == WEAPON_TOOL and self.player_id != hit_player.player_id:
				self.current_target_position = (hit_player.world_object.position.x, hit_player.world_object.position.y, hit_player.world_object.position.z)
				self.current_shooter_position = (self.world_object.position.x, self.world_object.position.y, self.world_object.position.z)
				self.current_hit_vector = tuple(map(operator.sub, self.current_target_position, self.current_shooter_position))
			
				self.vector_theta = self.vector_angle(self.current_hit_vector, self.previous_hit_vector)
				
				if self.vector_theta >= angle_threshold and self.update_count <= update_threshold and hit_amount == self.previous_hit_amount:
					irc_relay = protocol.irc_relay 
					if irc_relay.factory.bot and irc_relay.factory.bot.colors:
						irc_relay.send('\x0308* Aimbot Event Detected - %s #%d (%s) Snap Angle: %.2f Update Count: %d \x0f' % (self.name, self.player_id, self.address[0], self.vector_theta, self.update_count))
					else:
						protocol.irc_say('Aimbot Event Detected - %s #%d (%s) Snap Angle: %.2f Update Count: %d' % (self.name, self.player_id, self.address[0], self.vector_theta, self.update_count))

		
				self.update_count = 0
				self.previous_target_position = self.current_target_position
				self.previous_shooter_position = self.current_shooter_position
				self.previous_hit_vector = self.current_hit_vector
				self.previous_hit_amount = hit_amount
				
			
			return connection.on_hit(self, hit_amount, hit_player, type, grenade)
			
	return protocol, aimbanConnection	
	