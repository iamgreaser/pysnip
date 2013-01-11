from commands import name, add, admin, alias
@alias('staff')
@admin
def staff(connection):
    protocol = connection.protocol
    admin_message = "Admins logged in: "
    for conn in protocol.connections.values():
        if conn.admin:
            admin_message += "%s [A], " % conn.name
        elif conn.user_types is not None:
            if conn.user_types.moderator:
                admin_message += "%s [M], " % conn.name
            elif conn.user_types.guard:
                admin_message += "%s [G], " % conn.name
            elif conn.user_types.trusted:
                admin_message += "%s [T], " % conn.name
    if admin_message == "Admins logged in: ":
        admin_message = "No admins are logged in."
    else:
        admin_message = admin_message[:-2]
        if connection not in connection.protocol.players:
            admin_message += "\n [A]dmin [G]uard [T]rusted"
        else:
            connection.send_chat("[A]dmin [M]oderator [G]uard [T]rusted")
    return admin_message
add(staff)

def apply_script(protocol, connection, config):
    return protocol, connection
