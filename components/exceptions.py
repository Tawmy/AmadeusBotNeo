from discord.ext import commands


class BotNotConfigured(commands.CheckFailure):
    def __init__(self, *args):
        self.description = "The bot is not configured on this server. Please make sure the server owner runs the `!setup` command. They can optinally specify another user to run the setup for them."
        message = "Bot not configured"
        super().__init__(message, *args)


class BotDisabled(commands.CheckFailure):
    def __init__(self, *args):
        self.description = "The bot is disabled on this server. It will not respond to any commands."
        message = "Bot disabled"
        super().__init__(message, *args)


class CategoryDisabled(commands.CheckFailure):
    def __init__(self):
        self.description = "This command category is disabled on this server."
        message = "Category disabled"
        super().__init__(message)


class CategoryRoleRestricted(commands.CheckFailure):
    def __init__(self):
        message = "Role restricted category"
        super().__init__(message)


class CategoryNoWhitelistedRole(CategoryRoleRestricted):
    def __init__(self, missing_roles):
        self.description = "You do not have any of the roles required to run commands from this category:\n\n**"
        self.missing_roles = []

        for role in missing_roles:
            self.missing_roles.append(role.name)

        self.description += '**, **'.join(self.missing_roles)
        self.description += "**"

        super().__init__()


class CategoryBlacklistedRole(CategoryRoleRestricted):
    def __init__(self, role):
        self.role = role.name
        self.description = "You have a role that forbids you from using commands from this category:\n\n"
        self.description += "**" + self.role + "**"
        super().__init__()


class CommandDisabled(commands.CheckFailure):
    def __init__(self, *args):
        message = "Command disabled"
        self.description = "This command is disabled on this server."
        super().__init__(message, *args)


class CommandChannelRestricted(commands.CheckFailure):
    def __init__(self):
        message = "Channel restricted command"
        super().__init__(message)


class CommandNotWhitelistedChannel(CommandChannelRestricted):
    def __init__(self):
        self.description = "This command is not enabled in this channel."
        super().__init__()


class CommandBlacklistedChannel(CommandChannelRestricted):
    def __init__(self):
        self.description = "This command is disabled in this channel."
        super().__init__()


class CommandRoleRestricted(commands.CheckFailure):
    def __init__(self):
        message = "Role restricted command"
        super().__init__(message)


class CommandNoWhitelistedRole(CommandRoleRestricted):
    def __init__(self, missing_roles):
        self.description = "You do not have any of the roles required to run this command:\n\n**"
        self.missing_roles = []

        for role in missing_roles:
            self.missing_roles.append(role.name)

        self.description += '**, **'.join(self.missing_roles)
        self.description += "**"

        super().__init__()


class CommandBlacklistedRole(CommandRoleRestricted):
    def __init__(self, role):
        self.role = role.name
        self.description = "You have a role that forbids you from using this command:\n\n"
        self.description += "**" + self.role + "**"
        super().__init__()

# TODO time exceptions

