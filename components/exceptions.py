from discord.ext import commands


class BotNotReady(commands.CheckFailure):
    def __init__(self):
        message = "Bot is not ready"
        super().__init__(message)


class NoDirectMessages(commands.CheckFailure):
    def __init__(self):
        message = "Not permitted in DMs"
        super().__init__(message)


class CorruptConfig(commands.CheckFailure):
    def __init__(self):
        message = "Corrupt configuration"
        super().__init__(message)


class DatabaseNotConnected(commands.CheckFailure):
    def __init__(self):
        message = "Database not connected"
        super().__init__(message)


class NotGuildOwner(commands.CheckFailure):
    def __init__(self):
        message = "Not server owner"
        super().__init__(message)


class BotNotConfigured(commands.CheckFailure):
    def __init__(self, *args):
        message = "Bot not configured"
        super().__init__(message, *args)


class BotDisabled(commands.CheckFailure):
    def __init__(self, *args):
        message = "Bot disabled"
        super().__init__(message, *args)


class CategoryDisabled(commands.CheckFailure):
    def __init__(self):
        message = "Category disabled"
        super().__init__(message)


class CategoryNoWhitelistedRole(commands.CheckFailure):
    def __init__(self, roles):
        message = "Role restricted category"
        self.roles = []

        for role in roles:
            self.roles.append(role.name)

        super().__init__(message)


class CategoryBlacklistedRole(commands.CheckFailure):
    def __init__(self, role):
        message = "Role restricted category"
        self.role = role.name
        super().__init__(message)


class CommandDisabled(commands.CheckFailure):
    def __init__(self, *args):
        message = "Command disabled"
        super().__init__(message, *args)


class CommandNotWhitelistedChannel(commands.CheckFailure):
    def __init__(self):
        message = "Channel restricted command"
        super().__init__(message)


class CommandBlacklistedChannel(commands.CheckFailure):
    def __init__(self):
        message = "Channel restricted command"
        super().__init__(message)


class CommandNoWhitelistedRole(commands.CheckFailure):
    def __init__(self, missing_roles):
        message = "Role restricted command"
        self.roles = []

        for role in missing_roles:
            self.roles.append(role.name)

        super().__init__(message)


class CommandBlacklistedRole(commands.CheckFailure):
    def __init__(self, role):
        message = "Role restricted command"
        self.role = role.name
        super().__init__(message)

# TODO time exceptions
