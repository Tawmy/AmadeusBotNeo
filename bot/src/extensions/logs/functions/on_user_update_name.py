from datetime import datetime

from discord import User, TextChannel, Embed
from discord.ext.commands import Bot

from database.models import Name, NameType
from extensions.logs import helper
from extensions.logs.enums import ParentType
from helpers import strings as s
from extensions.config import helper as c


async def iterate_and_log(bot: Bot, before: User, after: User):
    for guild in bot.guilds:
        if any(x for x in guild.members if x.id == after.id):
            if await c.get_config("logs", "name_local", bot=bot, guild_id=guild.id):
                log_channel = await helper.get_log_channel(bot, guild.id, "name_channel")
                if log_channel is not None:
                    await __log_local(bot, before, after, guild.id, log_channel)
        if await c.get_config("logs", "name_database", bot=bot, guild_id=guild.id):
            await __log_database(bot, before, after, guild.id)

async def __log_local(bot: Bot, before: User, after: User, guild_id: int, log_channel: TextChannel):
    embed = Embed()
    embed.title = await s.get_string("logs", "name_changed", bot=bot, guild_id=guild_id)
    embed = await helper.add_title(bot, embed, guild_id, "name_changed")
    embed = await helper.add_author(bot, embed, guild_id, user=after)
    embed = await __add_name_local(bot, after, embed, "after", guild_id)
    embed = await __add_name_local(bot, before, embed, "before", guild_id)
    await log_channel.send(embed=embed)


async def __add_name_local(bot: Bot, user: User, embed: Embed, string_title: str, guild_id: int) -> Embed:
    title = await s.get_string("logs", string_title, bot=bot, guild_id=guild_id)
    embed.add_field(name=title.string, value=user.name, inline=False)
    return embed


async def __log_database(bot: Bot, before: User, after: User, guild_id: int):
    db_entry = Name()
    db_entry.name_type = NameType.USERNAME
    db_entry.user_id = after.id
    db_entry.set_at = datetime.utcnow()
    db_entry.guild_id = guild_id
    db_entry.name_after = after.name
    db_entry.name_before = before.name
    await helper.add_parent_to_db(bot, ParentType.USER, after.id)
    await helper.add_parent_to_db(bot, ParentType.GUILD, guild_id)
    bot.db_session.add(db_entry)
    bot.db_session.commit()