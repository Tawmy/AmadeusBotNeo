from components import exceptions as ex


def is_guild_owner(ctx):
    if ctx.author != ctx.guild.owner:
        raise ex.NotGuildOwner(ctx.guild.owner)
    else:
        return True


def block_dms(ctx):
    if ctx.guild is None:
        raise ex.NoDirectMessages
    else:
        return True
