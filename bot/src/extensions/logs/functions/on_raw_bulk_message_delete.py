from discord import RawBulkMessageDeleteEvent, Embed, TextChannel
from discord.ext.commands import Bot

from extensions.config import helper as c
from helpers import strings as s
from extensions.logs import helper


async def log(bot: Bot, payload: RawBulkMessageDeleteEvent):
    if await c.get_config("logs", "message_delete_local", bot=bot, guild_id=payload.guild_id):
        log_channel = await helper.get_log_channel(bot, payload.guild_id, "message_delete_channel")
        if log_channel is not None:
            await __log_local(bot, payload, log_channel)


async def __log_local(bot: Bot, payload: RawBulkMessageDeleteEvent, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, payload.guild_id, "message_deleted_bulk")
    embed = await __add_description(bot, payload, embed)
    embed = await __add_event_channel(bot, payload, embed)
    await log_channel.send(embed=embed)


async def __add_description(bot: Bot, payload: RawBulkMessageDeleteEvent, embed: Embed) -> Embed:
    description = await s.get_string("logs", "message_deleted_bulk_description", bot=bot, guild_id=payload.guild_id)
    embed.description = description.string
    return embed


async def __add_event_channel(bot: Bot, payload: RawBulkMessageDeleteEvent, embed: Embed) -> Embed:
    event_channel = bot.get_channel(payload.channel_id)
    string = await s.get_string("logs", "channel", bot=bot, guild_id=payload.guild_id)
    embed.add_field(name=string.string, value=event_channel.mention)
    return embed


async def __add_count(bot: Bot, payload: RawBulkMessageDeleteEvent, embed: Embed) -> Embed:
    if payload.message_ids is not None:
        count = len(payload.message_ids)
    else:
        count = 0
    string = await s.get_string("logs", "count", bot=bot, guild_id=payload.guild_id)
    embed.add_field(name=string.string, value=str(count))
    return embed
