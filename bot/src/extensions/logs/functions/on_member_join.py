import calendar
from datetime import datetime

from discord import Embed, Member, TextChannel
from discord.ext.commands import Bot

from helpers import strings as s
from extensions.config import helper as c
from extensions.logs import helper
from helpers.strings import InsertPosition


async def log(bot: Bot, member: Member):
    if await c.get_config("logs", "member_join_local", bot=bot, guild_id=member.guild.id):
        log_channel = await helper.get_log_channel(bot, member.guild.id, "member_channel")
        if log_channel is not None:
            await __log_local(bot, member, log_channel)


async def __log_local(bot: Bot, member: Member, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, member.guild.id, "member_join")
    embed.description = f"{member.mention}\n*{str(member)}*"
    embed = await __add_footer(bot, member, embed)
    embed.set_thumbnail(url=member.avatar_url_as(static_format="png", size=256))
    embed.colour = 5877227
    await log_channel.send(embed=embed)


async def __add_footer(bot: Bot, member: Member, embed: Embed) -> Embed:
    time_difference_account_creation = datetime.utcnow() - member.created_at
    if time_difference_account_creation.days < 30:
        strings_to_be_inserted = [f"{time_difference_account_creation.days}", f"{time_difference_account_creation.seconds//3600}", f"{time_difference_account_creation.seconds//60}"]
        string = await s.get_string("logs", "created_relative", bot=bot, guild_id=member.guild.id)
    else:
        strings_to_be_inserted = [f"{member.created_at.day:02d}. {calendar.month_abbr[member.created_at.month]} {member.created_at.year}"]
        string = await s.get_string("logs", "created_absolute", bot=bot, guild_id=member.guild.id)
    string_processed = await s.insert_into_string(strings_to_be_inserted, string.list, InsertPosition.RIGHT)
    embed.set_footer(text=string_processed.string_combined)
    return embed