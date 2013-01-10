def apply_script(protocol, connection, config):
    class UserBlockProtocol(protocol):
        def on_map_change(self, map):
            extensions = self.map_info.extensions
            if extensions.has_key('user_blocks_only'):
                if extensions['user_blocks_only'] == True:    
                    self.user_blocks = set()
                else:
                    self.user_blocks = None
            else:
                self.user_blocks = None # default normal
    return UserBlockProtocol, connection