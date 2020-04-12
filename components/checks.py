from components import exceptions as ex


def is_guild_owner(ctx):
    if ctx.author != ctx.guild.owner:
        raise ex.NotGuildOwner(ctx.guild.owner)
    else:
        return True