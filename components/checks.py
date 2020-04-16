from components import exceptions as ex


def is_guild_owner(ctx):
    if ctx.author != ctx.guild.owner:
        raise ex.NotGuildOwner
    else:
        return True


def block_dms(ctx):
    if ctx.guild is None:
        raise ex.NoDirectMessages
    else:
        return True


def needs_database(ctx):
    if ctx.bot.database_pool is None:
        raise ex.DatabaseNotConnected
    else:
        return True
