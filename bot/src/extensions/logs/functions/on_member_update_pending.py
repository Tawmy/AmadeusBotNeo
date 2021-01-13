from discord import Member, TextChannel, Embed
from discord.ext.commands import Bot

from extensions.config import helper as c
from extensions.logs import helper


async def log(bot: Bot, before: Member, after: Member):
    if await c.get_config("logs", "member_pending_local", bot=bot, guild_id=after.guild.id):
        log_channel = await helper.get_log_channel(bot, after.guild.id, "member_channel")
        if log_channel is not None:
            await __log_local(bot, after, log_channel)


async def __log_local(bot: Bot, after: Member, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, after.guild.id, "member_pending")
    embed.description = f"{after.mention}\n*{str(after)}*"
    time_str = await helper.add_footer_joined(bot, after, embed, True)
    embed = await helper.add_footer_created(bot, after, embed, time_str)
    embed.set_thumbnail(url=after.avatar_url_as(static_format="png", size=256))
    embed.colour = 5877227
    await log_channel.send(embed=embed)