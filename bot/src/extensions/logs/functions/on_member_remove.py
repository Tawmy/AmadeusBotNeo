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
    embed = await __add_footer(bot, member, embed)
    embed.set_thumbnail(url=member.avatar_url_as(static_format="png", size=256))
    embed.colour = 14365000
    await log_channel.send(embed=embed)


async def __add_footer(bot: Bot, member: Member, embed: Embed) -> Embed:
    time_difference_member_joined = datetime.utcnow() - member.joined_at
    if time_difference_member_joined.days < 30:
        string_to_be_inserted = await helper.get_time(bot, member.guild.id, time_difference_member_joined)
        strings_to_be_inserted = [string_to_be_inserted]
        strings = await s.get_string("logs", "joined_relative", bot=bot, guild_id=member.guild.id)
    else:
        strings_to_be_inserted = [f"{member.joined_at.day:02d}. {calendar.month_abbr[member.joined_at.month]} {member.joined_at.year}"]
        strings = await s.get_string("logs", "joined_absolute", bot=bot, guild_id=member.guild.id)
    time_str = await s.insert_into_string(strings_to_be_inserted, strings.list, InsertPosition.RIGHT)
    embed.set_footer(text=time_str.string_combined)
    return embed