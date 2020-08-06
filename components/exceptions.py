from discord.ext import commands


class BotNotReady(commands.CheckFailure):
    """
    Thrown when the bot has not finished its boot sequence yet.
    This sequence ends before the bot tries to connect to its database.
    """
    def __init__(self):
        message = "Bot is not ready"
        super().__init__(message)


class NoDirectMessages(commands.CheckFailure):
    """
    Thrown by block_dms check when a user tries to run a command in DMs.
    """
    def __init__(self):
        message = "Not permitted in DMs"
        super().__init__(message)


class CorruptConfig(commands.CheckFailure):
    """
    Thrown when a guild's config could not be loaded and a function tries to access it.
    """
    def __init__(self):
        message = "Corrupt configuration"
        super().__init__(message)


class DatabaseNotConnected(commands.CheckFailure):
    """
    Thrown by needs_database check if user runs a command that requires a database connection
    while said database is not connected.
    """
    def __init__(self):
        message = "Database not connected"
        super().__init__(message)


class NotGuildOwner(commands.CheckFailure):
    """
    Thrown by is_guild_owner check if user is not guild owner.
    """
    def __init__(self):
        message = "Not server owner"
        super().__init__(message)


class BotNotConfigured(commands.CheckFailure):
    """
    Thrown when user tries to run any command while setup has not been run in the guild yet.
    """
    def __init__(self, *args):
        message = "Bot not configured"
        super().__init__(message, *args)


class BotDisabled(commands.CheckFailure):
    """
    Thrown when bot is disabled in a guild.
    """
    def __init__(self, *args):
        message = "Bot disabled"
        super().__init__(message, *args)


class CategoryDisabled(commands.CheckFailure):
    """
    Thrown when category the command is part of is disabled.
    """
    def __init__(self):
        message = "Category disabled"
        super().__init__(message)


class CategoryNoWhitelistedRole(commands.CheckFailure):
    """
    Thrown when user does not have any of the whitelisted roles for a category.
    Includes roles list with roles on whitelist.
    """
    def __init__(self, roles):
        message = "Role restricted category"
        self.roles = []

        for role in roles:
            self.roles.append(role.name)

        super().__init__(message)


class CategoryBlacklistedRole(commands.CheckFailure):
    """
    Thrown when user does have one of the blacklisted roles for a category.
    Includes blacklisted role.
    """
    def __init__(self, role):
        message = "Role restricted category"
        self.role = role.name
        super().__init__(message)


class CommandDisabled(commands.CheckFailure):
    """
    Thrown when command is disabled in the guild.
    """
    def __init__(self, *args):
        message = "Command disabled"
        super().__init__(message, *args)


class CommandNotWhitelistedChannel(commands.CheckFailure):
    """
    Thrown when command is run in a channel that is not part of the whitelist.
    """
    def __init__(self):
        message = "Channel restricted command"
        super().__init__(message)


class CommandBlacklistedChannel(commands.CheckFailure):
    """
    Thrown when command is run in a channel that is part of the blacklist.
    """
    def __init__(self):
        message = "Channel restricted command"
        super().__init__(message)


class CommandNoWhitelistedRole(commands.CheckFailure):
    """
    Thrown when user does not have any of the whitelisted roles for a command.
    Includes list of whitelisted roles.
    """
    def __init__(self, missing_roles):
        message = "Role restricted command"
        self.roles = []

        for role in missing_roles:
            self.roles.append(role.name)

        super().__init__(message)


class CommandBlacklistedRole(commands.CheckFailure):
    """
    Thrown when user does have one of the blacklisted roles for a command.
    Includes blacklisted role.
    """
    def __init__(self, role):
        message = "Role restricted command"
        self.role = role.name
        super().__init__(message)

# TODO time exceptions
