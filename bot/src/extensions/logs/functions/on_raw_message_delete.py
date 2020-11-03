from datetime import datetime
from os.path import basename
from urllib.parse import urlparse

import discord
from discord import RawMessageDeleteEvent, TextChannel, Embed, NotFound
from discord.ext.commands import Bot

from database.models import Message, MessageEventType, Attachment
from extensions.config import helper as c
from extensions.logs import helper
from helpers import strings as s


async def log(bot: Bot, payload: RawMessageDeleteEvent):
    if await c.get_config("logs", "message_delete_local", bot=bot, guild_id=payload.guild_id):
        channel_config = await c.get_config("logs", "message_delete_channel", bot=bot, guild_id=payload.guild_id)
        if channel_config.value is not None:
            log_channel = bot.get_channel(int(channel_config.value))
            if log_channel is None:
                # fall back to log channel if configured channel not found
                log_channel = await helper.get_log_channel(bot, payload.guild_id)
        else:
            log_channel = await helper.get_log_channel(bot, payload.guild_id)

        if log_channel is not None:
            if payload.cached_message is not None:
                await __log_cached_local(bot, payload, log_channel)
            else:
                await __log_not_cached(bot, payload, log_channel)

    if payload.cached_message is not None:
        if await c.get_config("logs", "message_delete_database", bot=bot, guild_id=payload.guild_id):
            await __log_cached_database(bot, payload)


async def __log_not_cached(bot: Bot, payload: RawMessageDeleteEvent, log_channel: TextChannel):
    embed = Embed()
    title = await s.get_string("logs", "message_deleted", bot=bot, guild_id=payload.guild_id)
    embed.title = title.string
    description = await s.get_string("logs", "message_deleted_unknown_description", bot=bot, guild_id=payload.guild_id)
    embed.description = description.string
    channel = bot.get_channel(payload.channel_id)
    channel_title = await s.get_string("logs", "channel", bot=bot, guild_id=payload.guild_id)
    embed.add_field(name=channel_title.string, value=channel.mention)
    await log_channel.send(embed=embed)


async def __log_cached_local(bot: Bot, payload: RawMessageDeleteEvent, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, payload.guild_id, "message_deleted")
    embed = await helper.add_author(bot, embed, payload.cached_message, payload.guild_id)
    embed = await helper.add_channel(bot, embed, payload.guild_id, payload.channel_id)
    embed = await __add_content_local(bot, payload, embed)
    embed = await __add_counts_local(bot, payload, embed)
    embed = await __add_mentions(bot, payload, embed)
    embed = await __add_attachment_list_and_image(bot, payload, embed)
    embed = await helper.add_footer(payload.cached_message, embed)
    await log_channel.send(embed=embed)


async def __log_cached_database(bot: Bot, payload: RawMessageDeleteEvent):
    db_entry = Message()
    db_entry.id = payload.cached_message.id
    db_entry.guild_id = payload.guild_id
    db_entry.channel_id = payload.channel_id
    db_entry.user_id = payload.cached_message.author.id
    db_entry.created_at = payload.cached_message.created_at

    db_entry = await __add_content_database(payload, db_entry)
    db_entry = await __add_counts_database(payload, db_entry)

    db_entry.event_type = MessageEventType.DELETE
    db_entry.event_at = datetime.utcnow()

    await helper.add_user_to_db(bot, payload.cached_message.author.id)
    await __save_to_database(bot, db_entry)
    if payload.cached_message.attachments is not None and len(payload.cached_message.attachments) > 0:
        await __log_attachments(bot, payload)
    bot.db_session.commit()


async def __add_content_database(payload: RawMessageDeleteEvent, db_entry: Message) -> Message:
    if payload.cached_message.content is not None and len(payload.cached_message.content) > 0:
        db_entry.content = payload.cached_message.content
    else:
        db_entry.content = str()
    return db_entry


async def __add_content_local(bot: Bot, payload: RawMessageDeleteEvent, embed: Embed) -> Embed:
    if payload.cached_message.content is not None and len(payload.cached_message.content) > 0:
        content_title = await s.get_string("logs", "content", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=content_title.string, value=payload.cached_message.content, inline=False)
    return embed


async def __add_counts_local(bot: Bot, payload: RawMessageDeleteEvent, embed: Embed) -> Embed:
    if payload.cached_message.attachments is not None and len(payload.cached_message.attachments) > 0:
        attachment_title = await s.get_string("logs", "attachments", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=attachment_title.string, value=str(len(payload.cached_message.attachments)))
    if payload.cached_message.embeds is not None and len(payload.cached_message.embeds) > 0:
        embeds_title = await s.get_string("logs", "embeds", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=embeds_title.string, value=str(len(payload.cached_message.embeds)))
    return embed


async def __add_counts_database(payload: RawMessageDeleteEvent, db_entry: Message) -> Message:
    if payload.cached_message.mentions is not None and len(payload.cached_message.mentions) > 0:
        db_entry.count_mentions = len(payload.cached_message.mentions)
    else:
        db_entry.count_mentions = 0
    if payload.cached_message.attachments is not None and len(payload.cached_message.attachments) > 0:
        db_entry.count_attachments = len(payload.cached_message.attachments)
    else:
        db_entry.count_attachments = 0
    if payload.cached_message.embeds is not None and len(payload.cached_message.embeds) > 0:
        db_entry.count_embeds = len(payload.cached_message.embeds)
    else:
        db_entry.count_embeds = 0
    return db_entry


async def __add_mentions(bot: Bot, payload: RawMessageDeleteEvent, embed: Embed) -> Embed:
    mentions_count = 0
    if payload.cached_message.mentions is not None and len(payload.cached_message.mentions) > 0:
        mentions_count += len(payload.cached_message.mentions)
    if payload.cached_message.role_mentions is not None and len(payload.cached_message.role_mentions) > 0:
        mentions_count += len(payload.cached_message.role_mentions)
    if mentions_count > 0:
        mentions_title = await s.get_string("logs", "mentions", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=mentions_title.string, value=str(mentions_count))
    return embed


async def __add_attachment_list_and_image(bot: Bot, payload: RawMessageDeleteEvent, embed: Embed) -> Embed:
    image_is_set = False
    image_url = ""
    if payload.cached_message.attachments is not None and len(payload.cached_message.attachments) > 0:
        attachment_url_list = []
        for attachment in payload.cached_message.attachments:
            attachment_url_list.append(attachment.proxy_url)
            if image_is_set is False and await helper.is_image(attachment.proxy_url):
                image_is_set = True
                image_url = attachment.proxy_url
        attachment_list_title = await s.get_string("logs", "attachment_list", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=attachment_list_title.string, value="\n\n".join(attachment_url_list))
    if payload.cached_message.embeds is not None and len(payload.cached_message.embeds) > 0:
        for inner_embed in payload.cached_message.embeds:
            if image_is_set is False and await helper.is_image(inner_embed.url):
                image_is_set = True
                image_url = inner_embed.url
    if image_is_set:
        embed.set_image(url=image_url)
    return embed


async def __log_attachments(bot: Bot, payload: RawMessageDeleteEvent):
    for attachment in payload.cached_message.attachments:
        db_entry = Attachment()
        db_entry.message_id = payload.cached_message.id
        parsed_url = urlparse(attachment.proxy_url)
        db_entry.filename = basename(parsed_url.path)
        bot.db_session.add(db_entry)
        bot.db_session.flush()
        await __save_attachment(attachment, db_entry)
        # TODO handle errors (maybe output message in log channel)


async def __save_attachment(attachment: discord.Attachment, db_entry: Attachment) -> bool:
    path = "files/attachments/" + str(db_entry.id)
    try:
        await attachment.save(path, use_cached=True)
        return True
    except NotFound:
        pass
    try:
        await attachment.save(path)
        return True
    except NotFound:
        pass
    return False


async def __save_to_database(bot: Bot, db_entry: Message):
    db_object = bot.db_session.query(Message).filter_by(id=db_entry.id).first()
    if db_object:
        db_object.content = db_entry.content
        db_object.count_mentions = db_entry.count_mentions
        db_object.count_attachments = db_entry.count_attachments
        db_object.count_embeds = db_entry.count_embeds
        db_object.event_at = db_entry.event_at
        db_object.event_type = MessageEventType.DELETE
    else:
        bot.db_session.add(db_entry)
