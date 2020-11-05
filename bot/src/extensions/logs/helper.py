from discord import TextChannel, Message, Embed
from discord.ext.commands import Bot

from database.models import User, Guild
from extensions.config import helper as c
from extensions.logs.enums import ParentType
from helpers import strings as s


async def get_log_channel(bot: Bot, guild_id: int) -> TextChannel:
    log_channel_id = await c.get_config("essential_channels", "log_channel", bot=bot, guild_id=guild_id)
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


async def add_parent_to_db(bot: Bot, parent_type: ParentType, id: int):
    obj = None
    if parent_type == ParentType.GUILD:
        obj = Guild
    elif parent_type == ParentType.USER:
        obj = User
    if obj is None:
        return
    db_object = bot.db_session.query(obj).filter_by(id=id).first()
    if db_object:
        return
    else:
        db_entry = obj()
        db_entry.id = id
        bot.db_session.add(db_entry)
        # TODO check if this works without commit


async def add_title(bot: Bot, embed: Embed, guild_id: int, string_name: str) -> Embed:
    title = await s.get_string("logs", string_name, bot=bot, guild_id=guild_id)
    embed.title = title.string
    return embed


async def add_author(bot: Bot, embed: Embed, cached_message: Message, guild_id: int):
    title = await s.get_string("logs", "user", bot=bot, guild_id=guild_id)
    embed.add_field(name=title.string, value=cached_message.author.mention)
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
