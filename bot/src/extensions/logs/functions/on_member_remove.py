import calendar
from datetime import datetime

from discord import Member, TextChannel, Embed
from discord.ext.commands import Bot

from extensions.config import helper as c
from helpers import strings as s
from extensions.logs import helper
from helpers.strings import InsertPosition


async def log(bot: Bot, member: Member):
    if await c.get_config("logs", "member_leave_local", bot=bot, guild_id=member.guild.id):
        log_channel = await helper.get_log_channel(bot, member.guild.id, "member_channel")
        if log_channel is not None:
            await __log_local(bot, member, log_channel)


async def __log_local(bot: Bot, member: Member, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, member.guild.id, "member_leave")
    embed.description = f"**{str(member)}**\n`{str(member.id)}`"
    embed = await helper.add_footer_joined(bot, member, embed)
    embed.set_thumbnail(url=member.avatar_url_as(static_format="png", size=256))
    embed.colour = 14365000
    await log_channel.send(embed=embed)