from datetime import timedelta, datetime

import calendar
from typing import Union

import discord
from discord import TextChannel, Message, Embed, Member
from discord.ext.commands import Bot

from database.models import User, Guild
from extensions.config import helper as c
from extensions.logs.enums import ParentType
from helpers import strings as s
from helpers.strings import InsertPosition


async def get_log_channel(bot: Bot, guild_id: int, config_option: str):
    channel_config = await c.get_config("logs", config_option, bot=bot, guild_id=guild_id)
    if channel_config.value is not None and len(channel_config.value) > 0:
        log_channel = bot.get_channel(int(channel_config.value))
        if log_channel is None:
            # fall back to log channel if configured channel not found
            log_channel = await __get_essential_log_channel(bot, guild_id)
    else:
        log_channel = await __get_essential_log_channel(bot, guild_id)
    return log_channel


async def __get_essential_log_channel(bot: Bot, guild_id: int) -> TextChannel:
    log_channel_id = await c.get_config("essential_channels", "log_channel", bot=bot, guild_id=guild_id)
    # TODO possibly security hole here, could enter another server's channel ID?
    return bot.get_channel(log_channel_id.value)


async def is_image(url) -> bool:
    # TODO check which image types are supported
    if not isinstance(url, str):
        return False
    if url[-4:] in [".jpg", ".png"]:
        return True
    if url[-5:] in [".jpeg", ".webp"]:
        return True
    return False


async def add_parent_to_db(bot: Bot, parent_type: ParentType, obj_id: int):
    obj = None
    if parent_type == ParentType.GUILD:
        obj = Guild
    elif parent_type == ParentType.USER:
        obj = User
    if obj is None:
        return
    db_object = bot.db_session.query(obj).filter_by(id=obj_id).first()
    if db_object:
        return
    else:
        db_entry = obj()
        db_entry.id = obj_id
        bot.db_session.add(db_entry)
        # TODO check if this works without commit


async def add_title(bot: Bot, embed: Embed, guild_id: int, string_name: str) -> Embed:
    title = await s.get_string("logs", string_name, bot=bot, guild_id=guild_id)
    embed.title = title.string
    return embed


async def add_author(bot: Bot, embed: Embed, guild_id: int, message: Message = None, member: Member = None, user: discord.User = None):
    title = await s.get_string("logs", "user", bot=bot, guild_id=guild_id)
    if message is not None:
        embed.add_field(name=title.string, value=message.author.mention)
    elif member is not None:
        embed.add_field(name=title.string, value=member.mention)
    elif user is not None:
        embed.add_field(name=title.string, value=user.mention)
    return embed


async def add_channel(bot: Bot, embed: Embed, guild_id: int, channel_id: int) -> Embed:
    channel_title = await s.get_string("logs", "channel", bot=bot, guild_id=guild_id)
    channel = bot.get_channel(channel_id)
    embed.add_field(name=channel_title.string, value=channel.mention)
    return embed


async def add_footer(cached_message: Message, embed: Embed) -> Embed:
    text = cached_message.created_at.replace(microsecond=0)
    icon_url = "https://i.imgur.com/FkOFUCC.png"
    embed.set_footer(text=text, icon_url=icon_url)
    return embed


async def add_footer_joined(bot: Bot, member: Member, embed: Embed, return_str: bool = False) -> Union[Embed, str]:
    time_difference_member_joined = datetime.utcnow() - member.joined_at
    if time_difference_member_joined.days < 30:
        string_to_be_inserted = await get_time(bot, member.guild.id, time_difference_member_joined)
        strings_to_be_inserted = [string_to_be_inserted]
        strings = await s.get_string("logs", "joined_relative", bot=bot, guild_id=member.guild.id)
    else:
        strings_to_be_inserted = [f"{member.joined_at.day:02d}. {calendar.month_abbr[member.joined_at.month]} {member.joined_at.year}"]
        strings = await s.get_string("logs", "joined_absolute", bot=bot, guild_id=member.guild.id)
    time_str = await s.insert_into_string(strings_to_be_inserted, strings.list, InsertPosition.RIGHT)
    if return_str:
        return time_str.string_combined
    embed.set_footer(text=time_str.string_combined)
    return embed


async def add_footer_created(bot: Bot, member: Member, embed: Embed, string_to_be_appended: str = None) -> Embed:
    time_difference_account_creation = datetime.utcnow() - member.created_at
    if time_difference_account_creation.days < 30:
        string_to_be_inserted = await get_time(bot, member.guild.id, time_difference_account_creation)
        strings_to_be_inserted = [string_to_be_inserted]
        string = await s.get_string("logs", "created_relative", bot=bot, guild_id=member.guild.id)
    else:
        strings_to_be_inserted = [f"{member.created_at.day:02d}. {calendar.month_abbr[member.created_at.month]} {member.created_at.year}"]
        string = await s.get_string("logs", "created_absolute", bot=bot, guild_id=member.guild.id)
    string_processed = await s.insert_into_string(strings_to_be_inserted, string.list, InsertPosition.RIGHT)
    if string_to_be_appended is not None:
        embed.set_footer(text=f"{string_to_be_appended}\n{string_processed.string_combined}")
    else:
        embed.set_footer(text=string_processed.string_combined)
    return embed


async def get_time(bot: Bot, guild_id: int, delta: timedelta) -> str:
    if delta.days == 0 and delta.seconds < 60:
        string_seconds = await s.get_string("time", "seconds", bot=bot, guild_id=guild_id)
        return f"{delta.seconds} {string_seconds.string}"
    elif delta.days == 0 and delta.seconds < 3600:
        string_minutes = await s.get_string("time", "minutes", bot=bot, guild_id=guild_id)
        string_seconds = await s.get_string("time", "seconds", bot=bot, guild_id=guild_id)
        minutes, seconds = divmod(delta.seconds, 60)
        return f"{minutes} {string_minutes.string}, {seconds} {string_seconds.string}"
    elif delta.days == 0:
        string_hours = await s.get_string("time", "hours", bot=bot, guild_id=guild_id)
        string_minutes = await s.get_string("time", "minutes", bot=bot, guild_id=guild_id)
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} {string_hours.string}, {minutes} {string_minutes.string}"
    else:
        string_days = await s.get_string("time", "days", bot=bot, guild_id=guild_id)
        string_hours = await s.get_string("time", "hours", bot=bot, guild_id=guild_id)
        hours, remainder = divmod(delta.seconds, 3600)
        return f"{delta.days} {string_days.string}, {hours} {string_hours.string}"