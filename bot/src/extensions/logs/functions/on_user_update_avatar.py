from discord import User, TextChannel, Embed
from discord.ext.commands import Bot

from extensions.config import helper as c
from extensions.logs import helper


async def log(bot: Bot, before: User, after: User):
    for guild in bot.guilds:
        if any(x for x in guild.members if x.id == after.id):
            if await(c.get_config("logs", "avatar_local", bot=bot, guild_id=guild.id)):
                log_channel = await helper.get_log_channel(bot, guild.id, "avatar_channel")
                if log_channel is not None:
                    await __log_local(bot, before, after, guild.id, log_channel)


async def __log_local(bot: Bot, before: User, after: User, guild_id: int, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, guild_id, "avatar_changed")
    embed = await helper.add_author(bot, embed, guild_id, user=after)
    embed.set_thumbnail(url=after.avatar_url_as(static_format="png", size=256))
    await log_channel.send(embed=embed)
