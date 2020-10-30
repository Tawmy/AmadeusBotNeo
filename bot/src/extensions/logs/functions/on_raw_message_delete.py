from discord import RawMessageDeleteEvent, TextChannel, Embed
from discord.ext.commands import Bot

from extensions.config import helper as c
from extensions.logs import helper
from helpers import strings as s


async def log(bot: Bot, payload: RawMessageDeleteEvent):
    if not await c.get_config("logs", "message_delete", bot=bot, guild_id=payload.guild_id):
        return

    if await c.get_config("logs", "message_delete_local", bot=bot, guild_id=payload.guild_id):
        channel_config = await c.get_config("logs", "message_delete_chafnnel", bot=bot, guild_id=payload.guild_id)
        if channel_config.value is not None and len(channel_config.value) > 0:
            channel = bot.get_channel(int(channel_config.value))
            if channel is None:
                # fall back to log channel if configured channel not found
                channel = await __get_log_channel(bot, payload)
        else:
            channel = await __get_log_channel(bot, payload)

        if channel is not None:
            if payload.cached_message is not None:
                await __log_cached_local(bot, payload, channel)
            else:
                await __log_not_cached(bot, payload, channel)

    if await c.get_config("logs", "message_delete_database", bot=bot, guild_id=payload.guild_id):
        await __log_cached_database(bot, payload)


async def __log_not_cached(bot: Bot, payload: RawMessageDeleteEvent, channel):
    pass


async def __log_cached_local(bot: Bot, payload: RawMessageDeleteEvent, log_channel: TextChannel):
    embed = Embed()
    title = await s.get_string("logs", "message_deleted", bot=bot, guild_id=payload.guild_id)
    embed.title = title.string

    channel_title = await s.get_string("logs", "channel", bot=bot, guild_id=payload.guild_id)
    channel = bot.get_channel(payload.channel_id)
    embed.add_field(name=channel_title.string, value=channel.mention)

    embed = await __add_counts(bot, payload, embed)
    embed = await __add_mentions(bot, payload, embed)
    embed = await __add_attachment_list_and_image(bot, payload, embed)

    embed.set_footer(text=payload.cached_message.created_at.replace(microsecond=0), icon_url="https://i.imgur.com/FkOFUCC.png")

    await log_channel.send(embed=embed)


async def __log_cached_database(bot: Bot, payload: RawMessageDeleteEvent):
    pass


async def __get_log_channel(bot: Bot, payload: RawMessageDeleteEvent) -> TextChannel:
    log_channel_id = await c.get_config("essential_channels", "log_channel", bot=bot, guild_id=payload.guild_id)
    return bot.get_channel(log_channel_id.value)


async def __add_counts(bot: Bot, payload: RawMessageDeleteEvent, embed: Embed) -> Embed:
    if payload.cached_message.content is not None and len(payload.cached_message.content) > 0:
        content_title = await s.get_string("logs", "content", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=content_title.string, value=payload.cached_message.content, inline=False)
    if payload.cached_message.attachments is not None and len(payload.cached_message.attachments) > 0:
        attachment_title = await s.get_string("logs", "attachments", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=attachment_title.string, value=str(len(payload.cached_message.attachments)))
    if payload.cached_message.embeds is not None and len(payload.cached_message.embeds) > 0:
        embeds_title = await s.get_string("logs", "embeds", bot=bot, guild_id=payload.guild_id)
        embed.add_field(name=embeds_title.string, value=str(len(payload.cached_message.embeds)))
    return embed


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
