from components import exceptions as ex


def is_guild_owner(ctx):
    """
    Checks if context author is guild owner.
    Throws NotGuildOwner if false.
    """
    if ctx.author != ctx.guild.owner:
        raise ex.NotGuildOwner
    else:
        return True


def block_dms(ctx):
    """
    Checks if command is run in a DM.
    Throws NoDirectMessages if true.
    """
    if ctx.guild is None:
        raise ex.NoDirectMessages
    else:
        return True


def needs_database(ctx):
    """
    Checks if database is connected.
    Throws DatabaseNotConnected if not.
    """
    if ctx.bot.database_pool is None:
        raise ex.DatabaseNotConnected
    else:
        return True
