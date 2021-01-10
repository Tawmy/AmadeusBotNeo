from datetime import datetime

from discord import Member, Embed, TextChannel
from discord.ext.commands import Bot

from database.models import Name, NameType
from extensions.config import helper as c
from extensions.logs.enums import ParentType
from helpers import strings as s
from extensions.logs import helper


async def log(bot: Bot, before: Member, after: Member):
    if await c.get_config("logs", "name_local", bot=bot, guild_id=after.guild.id):
        log_channel = await helper.get_log_channel(bot, after.guild.id, "name_channel")
        if log_channel is not None:
            await __log_local(bot, before, after, log_channel)

    if await c.get_config("logs", "name_database", bot=bot, guild_id=after.guild.id):
       await __log_database(bot, before, after)


async def __log_local(bot: Bot, before: Member, after: Member, log_channel: TextChannel):
    embed = Embed()
    embed = await helper.add_title(bot, embed, after.guild.id, "nick_changed")
    embed = await helper.add_author(bot, embed, after.guild.id, member=after)
    embed = await __add_nick_local(bot, after, embed, "after")
    embed = await __add_nick_local(bot, before, embed, "before")
    await log_channel.send(embed=embed)


async def __add_nick_local(bot: Bot, member: Member, embed: Embed, string_title: str) -> Embed:
    title = await s.get_string("logs", string_title, bot=bot, guild_id=member.guild.id)
    embed.add_field(name=title.string, value=member.nick, inline=False)
    return embed


async def __log_database(bot: Bot, before: Member, after: Member):
    db_entry = Name()
    db_entry.name_type = NameType.NICKNAME
    db_entry.user_id = after.id
    db_entry.set_at = datetime.utcnow()
    db_entry.guild_id = after.guild.id
    db_entry.name_after = after.nick
    db_entry.name_before = before.nick
    await helper.add_parent_to_db(bot, ParentType.USER, after.id)
    await helper.add_parent_to_db(bot, ParentType.GUILD, after.guild.id)
    bot.db_session.add(db_entry)
    bot.db_session.commit()
