from discord import Embed, Member, TextChannel
from discord.ext.commands import Bot

from extensions.config import helper as c
from extensions.logs import helper


async def log(bot: Bot, member: Member):
    if await c.get_config("logs", "member_join_local", bot=bot, guild_id=member.guild.id):
        log_channel = await helper.get_log_channel(bot, member.guild.id, "member_channel")
        if log_channel is not None:
            await __log_local(bot, member, log_channel)


async def __log_local(bot: Bot, member: Member, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, member.guild.id, "member_join")
    embed.description = f"{member.mention}\n*{str(member)}*"
    embed = await helper.add_footer_created(bot, member, embed)
    embed.set_thumbnail(url=member.avatar_url_as(static_format="png", size=256))
    embed.colour = 5877227
    await log_channel.send(embed=embed)


