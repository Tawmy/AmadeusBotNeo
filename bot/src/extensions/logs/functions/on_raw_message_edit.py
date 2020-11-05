from datetime import datetime
from typing import Union

import discord
from ciso8601 import parse_datetime
from discord import RawMessageUpdateEvent, TextChannel, Embed
from discord.ext.commands import Bot

from database.models import Message, MessageEventType, MessageEdit
from extensions.config import helper as c
from extensions.logs import helper
from extensions.logs.enums import ParentType
from helpers import strings as s


async def log(bot: Bot, payload: RawMessageUpdateEvent):
    guild_id = payload.data["guild_id"]
    if await c.get_config("logs", "message_edit_local", bot=bot, guild_id=guild_id):
        channel_config = await c.get_config("logs", "message_edit_channel", bot=bot, guild_id=guild_id)
        if channel_config.value is not None:
            log_channel = bot.get_channel(int(channel_config.value))
            if log_channel is None:
                # fall back to log channel if configured channel not found
                log_channel = await helper.get_log_channel(bot, guild_id)
        else:
            log_channel = await helper.get_log_channel(bot, guild_id)

        if log_channel is not None:
            await __log_local(bot, payload, log_channel, guild_id)
    if await c.get_config("logs", "message_edit_database", bot=bot, guild_id=guild_id):
        await __log_database(bot, payload, guild_id)


async def __log_local(bot: Bot, payload: RawMessageUpdateEvent, log_channel: TextChannel, guild_id: int):
    embed = Embed()
    fetched_message = await __fetch_message(bot, payload)
    embed = await helper.add_title(bot, embed, guild_id, "message_edited")
    embed = await __add_author(bot, payload, embed, guild_id)
    embed = await helper.add_channel(bot, embed, guild_id, payload.channel_id)
    embed = await __add_link(bot, payload, embed, guild_id, fetched_message)
    embed = await __add_content_new(bot, payload, embed, guild_id)
    embed = await __add_content_old(bot, payload, embed, guild_id)
    embed = await __add_footer(payload, embed)
    await log_channel.send(embed=embed)


async def __fetch_message(bot: Bot, payload: RawMessageUpdateEvent) -> discord.Message:
    message = None
    if payload.cached_message is None:
        message_id = payload.data.get("id")
        if message_id is not None:
            channel = bot.get_channel(payload.channel_id)
            if channel is not None:
                message = await channel.fetch_message(message_id)
    return message


async def __add_author(bot: Bot, payload: RawMessageUpdateEvent, embed: Embed, guild_id: int) -> Embed:
    if payload.cached_message is not None:
        embed = await helper.add_author(bot, embed, payload.cached_message, guild_id)
    else:
        author_id = payload.data.get("author", {}).get("id")
        if author_id is not None:
            title = await s.get_string("logs", "user", bot=bot, guild_id=guild_id)
            embed.add_field(name=title.string, value="<@" + str(author_id) + ">")
    return embed


async def __add_link(bot: Bot, payload: RawMessageUpdateEvent, embed: Embed, guild_id: int, fetched_message: discord.Message) -> Embed:
    jump_url = None
    if payload.cached_message is not None:
        jump_url = payload.cached_message.jump_url
    elif fetched_message is not None:
        jump_url = fetched_message.jump_url
    if jump_url is not None:
        link_title = await s.get_string("logs", "message", bot=bot, guild_id=guild_id)
        link_value = await s.get_string("logs", "link", bot=bot, guild_id=guild_id)
        embed.add_field(name=link_title.string, value="[" + link_value.string + "](" + jump_url + ")")
    return embed


async def __add_content_new(bot: Bot, payload: RawMessageUpdateEvent, embed: Embed, guild_id: int) -> Embed:
    content_new = payload.data.get("content")
    if content_new is not None and len(content_new) > 0:
        content_new_title = await s.get_string("logs", "content_new", bot=bot, guild_id=guild_id)
        embed.add_field(name=content_new_title.string, value=content_new, inline=False)
    return embed


async def __add_content_old(bot: Bot, payload: RawMessageUpdateEvent, embed: Embed, guild_id: int) -> Embed:
    if payload.cached_message is not None and payload.cached_message.content is not None and len(payload.cached_message.content) > 0:
        content_old_title = await s.get_string("logs", "content_old", bot=bot, guild_id=guild_id)
        embed.add_field(name=content_old_title.string, value=payload.cached_message.content, inline=False)
    return embed


async def __add_footer(payload: RawMessageUpdateEvent, embed: Embed):
    if payload.cached_message is not None:
        embed = await helper.add_footer(payload.cached_message, embed)
    else:
        timestamp_str = payload.data.get("timestamp")
        if timestamp_str is not None:
            timestamp = parse_datetime(timestamp_str)
            text = timestamp.replace(microsecond=0, tzinfo=None)
            icon_url = "https://i.imgur.com/FkOFUCC.png"
            embed.set_footer(text=str(text), icon_url=icon_url)
    return embed


async def __log_database(bot: Bot, payload: RawMessageUpdateEvent, guild_id: int):
    # db_entry = Message()
    # db_entry = await __add_general_data_database(payload, db_entry)
    #
    # if payload.cached_message is not None:
    #     db_entry = await __add_cached_data_database(payload, db_entry)
    # else:
    #     status, db_entry = await __add_dict_data_database(payload, db_entry)
    #     if status is False:
    #         return
    #
    # status, db_entry = await __add_counts_from_dict_database(payload, db_entry)
    # if status is False:
    #     return
    #
    # await helper.add_user_to_db(bot, db_entry.user_id)
    # await __save_to_database(bot, db_entry)
    # bot.db_session.commit()

    db_entry_message = await __get_message_data(payload)
    if db_entry_message is None:
        return

    await helper.add_parent_to_db(bot, ParentType.GUILD, db_entry_message.guild_id)
    await helper.add_parent_to_db(bot, ParentType.USER, db_entry_message.user_id)

    await __save_message_to_database(bot, db_entry_message)
    bot.db_session.flush()

    db_entry_message_edit = await __get_message_edit_data(payload, db_entry_message.id)
    if db_entry_message_edit is None:
        return

    bot.db_session.add(db_entry_message_edit)
    bot.db_session.commit()


async def __get_message_data(payload: RawMessageUpdateEvent) -> Union[Message, None]:
    db_entry = Message()
    db_entry.id = payload.message_id
    db_entry.channel_id = payload.channel_id

    if payload.cached_message is not None:
        db_entry = await __get_message_data_cached(payload, db_entry)
    else:
        status, db_entry = await __get_message_data_dict(payload, db_entry)
        if status is False:
            return None

    status, db_entry = await __get_message_data_counts_cached(payload, db_entry)
    if status is False:
        return None

    return db_entry


async def __get_message_data_cached(payload: RawMessageUpdateEvent, db_entry: Message) -> Message:
    db_entry.guild_id = payload.cached_message.guild.id
    db_entry.user_id = payload.cached_message.author.id
    db_entry.created_at = payload.cached_message.created_at
    db_entry.count_mentions = len(payload.cached_message.mentions) if payload.cached_message.mentions is not None else 0
    db_entry.count_attachments = len(payload.cached_message.attachments) if payload.cached_message.attachments is not None else 0
    db_entry.count_embeds = len(payload.cached_message.embeds) if payload.cached_message.embeds is not None else 0
    return db_entry


async def __get_message_data_dict(payload: RawMessageUpdateEvent, db_entry: Message) -> [bool, Message]:
    if payload.data.get("guild_id") is not None:
        db_entry.guild_id = payload.data["guild_id"]
    else:
        return False, db_entry
    if payload.data.get("author", {}).get("id") is not None:
        user_id = payload.data["author"]["id"]
        db_entry.user_id = user_id
    else:
        return False, db_entry
    if payload.data.get("timestamp") is not None:
        db_entry.created_at = parse_datetime(payload.data["timestamp"])
    else:
        return False, db_entry
    return True, db_entry


async def __get_message_data_counts_cached(payload: RawMessageUpdateEvent, db_entry: Message) -> [bool, Message]:
    if payload.data.get("mentions") is not None:
        db_entry.count_mentions = len(payload.data["mentions"])
    elif db_entry.count_mentions is None:
        return False, db_entry
    if payload.data.get("attachments") is not None:
        db_entry.count_attachments = len(payload.data["attachments"])
    elif db_entry.count_attachments is None:
        return False, db_entry
    if payload.data.get("embeds") is not None:
        db_entry.count_embeds = len(payload.data["embeds"])
    elif db_entry.count_embeds is None:
        return False
    return True, db_entry


async def __save_message_to_database(bot: Bot, db_entry: Message):
    db_object = bot.db_session.query(Message).filter_by(id=db_entry.id).first()
    if db_object:
        db_object.count_mentions = db_entry.count_mentions
        db_object.count_attachments = db_entry.count_attachments
        db_object.count_embeds = db_entry.count_embeds
    else:
        bot.db_session.add(db_entry)


async def __get_message_edit_data(payload: RawMessageUpdateEvent, message_id: int) -> MessageEdit:
    db_entry = MessageEdit()
    db_entry.edited_at = datetime.utcnow()
    content_after = payload.data.get("content")
    if content_after is not None and len(content_after) > 0:
        db_entry.content_after = content_after
    if payload.cached_message is not None and payload.cached_message.content is not None and len(payload.cached_message.content) > 0:
        db_entry.content_before = payload.cached_message.content
    db_entry.message_id = message_id
    return db_entry
