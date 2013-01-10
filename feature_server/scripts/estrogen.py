from commands import add, admin, get_player
from pyspades.contained import BlockAction, SetColor
from pyspades.constants import *
import random

@admin
def estrogen(connection, player = None):
	if player is not None:
		player = get_player(connection.protocol, player)
	else:
		player = connection
	x, y, z = player.get_location()
	num = random.randrange(125, 150)
	connection.protocol.spawn_estrogen(x, y, z, num)
	player.send_chat('Let the female part of you emerge!')
	connection.protocol.send_chat('%s has been surrounded by a ' 
		'cloud of estrogen.' % (player.name), irc = True)
add(estrogen)

def apply_script(protocol, connection, config):
	class EstrogenProtocol(protocol):
		def spawn_estrogen(self, pos_x, pos_y, pos_z, number):
			for i in xrange(number):
				x, y, z = self.get_random_location(True, ((pos_x-15), (pos_y-15), 
						(pos_x+15), (pos_y+15)))
				z = pos_z - random.randrange(10)
				if z < 1: # going around 0 causes a crash. Let's have a safe limit
					continue
				self.place_estrogen_block(x, y, z)
			
		def place_estrogen_block(self, x, y, z):
			block_action = BlockAction()
			block_action.player_id = 31
			set_color = SetColor()
			set_color.value = 0xFF66FF
			set_color.player_id = block_action.player_id
			self.send_contained(set_color, save = True)
			self.map.set_point(x, y, z, (255, 102, 255))
			block_action.value = BUILD_BLOCK
			set_color.value = 0xFF66FF
			block_action.x = x
			block_action.y = y
			block_action.z = z
			self.send_contained(block_action, save = True)

	return EstrogenProtocol, connection
