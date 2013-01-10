from commands import add, admin, alias, name
redtext = False

@name('redtext')
@alias('red')
@admin
def toggle_red_text(connection):
    global redtext
    redtext = not redtext
add(toggle_red_text)
    
def apply_script(protocol, connection, config):
    class redtextConnection(connection):
        def on_chat(self, value, global_message):
            if global_message == True and not self.mute and redtext == True:
                if self.team is self.protocol.blue_team:
                    self.team_name = "Blue"
                elif self.team is self.protocol.green_team:
                    self.team_name = "Green"
                elif self.team.spectator:
                    self.team_name = "Spectator"
                self.msg = '%s (%s): %s' % (self.name, self.team_name, value)
                self.irc_msg = '<%s> (%s): %s' % (self.name, self.team_name, value)
                irc_relay = self.protocol.irc_relay
                irc_relay.send(self.irc_msg)
                self.static_player_list = self.protocol.players.values()
                for players in self.static_player_list:
                    players.send_chat(self.msg)
                return False
            return connection.on_chat(self, value, global_message)
    return protocol, redtextConnection