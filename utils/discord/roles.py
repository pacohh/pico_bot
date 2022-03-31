import discord


def has_any_roles(member, roles):
    """Check if the member has any of the given roles."""
    for role in roles:
        if has_role(member, role):
            return True
    return False


def has_role(member, role):
    """Check if the member has the given role."""
    if isinstance(role, discord.Role):
        role = role.id
    user_roles = {rol.id for rol in member.roles}
    return role in user_roles


def get_role_from_id(guild, role_id, default=None):
    """Get a discord.Role instance for the given role_id in guild."""
    role_id = int(role_id)
    roles = list(filter(lambda role: role.id == role_id, guild.roles))
    if not roles:
        return default
    else:
        return roles[0]
