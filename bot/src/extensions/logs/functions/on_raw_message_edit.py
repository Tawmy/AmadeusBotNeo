from ciso8601 import parse_datetime
from discord import RawMessageUpdateEvent, TextChannel, Embed, Message
from discord.ext.commands import Bot

from extensions.config import helper as c
from extensions.logs import helper
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


async def __fetch_message(bot: Bot, payload: RawMessageUpdateEvent) -> Message:
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


async def __add_link(bot: Bot, payload: RawMessageUpdateEvent, embed: Embed, guild_id: int, fetched_message: Message) -> Embed:
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
