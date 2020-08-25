import copy
import json
import os
import platform

import asyncio
from enum import Enum

import discord
from discord.ext import commands

from database import base as db
from database.base import DatabaseVersionStatus
from extensions.changelog.functions.addchangelog import save_changelog
from extensions.config.helper import load_values
from helpers import strings


class DatabaseStatus(Enum):
    CONNECTED = 0
    FAILED = 1
    UPGRADED = 2


async def startup_sequence(bot):
    # prepare init embeds for both main and all other servers
    init_embed, init_embed_extended = await prepare_init_embeds(bot)
    init_message_extended = await send_init_message_extended(bot, init_embed_extended)

    if init_message_extended is not None:
        # Load values
        values_status = await load_strings_and_values(bot)
        await update_init_embed_extended(bot, "values", init_embed_extended, values_status)
        await init_message_extended.edit(embed=init_embed_extended)

        # Stop bot if any value file could not be loaded
        if len(values_status) > 0:
            raise SystemExit()

        # Load extensions and update extended init message
        failed_extensions = await load_extensions(bot)
        await update_init_embed_extended(bot, "extensions", init_embed_extended, failed_extensions)
        await init_message_extended.edit(embed=init_embed_extended)

        # Check changelog, add to startup embed
        await check_changelog(bot, init_embed, init_embed_extended)

        # Load server configurations
        configs = await load_configs(bot)
        await update_init_embed_extended(bot, "configs", init_embed_extended, configs)
        await init_message_extended.edit(embed=init_embed_extended)

        bot.ready = True

        status = await connect_database(bot)
        await update_init_embed_extended(bot, "database", init_embed_extended, status)
        await init_message_extended.edit(embed=init_embed_extended)

        # Send startup message on all servers
        if bot.config["bot"]["debug"] is False:
            await send_startup_message(bot, init_embed)


async def prepare_init_embeds(bot):
    init_embed = discord.Embed()
    init_embed.title = bot.app_info.name
    init_embed.set_thumbnail(url="https://i.imgur.com/fvMdvyu.png")

    init_embed_extended = copy.deepcopy(init_embed)
    init_embed_extended.add_field(name="Extensions", value="⌛ Loading...")
    init_embed_extended.add_field(name="Strings", value="⌛ Waiting...")
    init_embed_extended.add_field(name="Configs", value="⌛ Waiting...")
    init_embed_extended.add_field(name="Database", value="⌛ Waiting...")
    init_embed_extended.add_field(name="Discord.py", value=discord.__version__)
    init_embed_extended.add_field(name="Python", value=platform.python_version())

    return [init_embed, init_embed_extended]


async def send_init_message_extended(bot, init_message_extended):
    channel = bot.get_channel(bot.config["bot"]["primary_server"]["main_channel_id"])
    if channel is not None:
        try:
            return await channel.send(embed=init_message_extended)
        except discord.Forbidden:
            print("Missing permissions, cannot send message.")
    else:
        print("Main channel not found, please fix this immediately.")


async def update_init_embed_extended(bot, update_type, init_embed_extended, value):
    if update_type == "values":
        if len(value) > 0:
            init_embed_extended.add_field(name="Values failed", value="\n".join(value), inline=False)
            init_embed_extended.set_field_at(0, name="Values", value="⚠ Failed")
            init_embed_extended.set_field_at(1, name="Extensions", value="🛑 Cancelled")
            init_embed_extended.set_field_at(2, name="Config", value="🛑 Cancelled")
        else:
            init_embed_extended.set_field_at(0, name="Values", value="✅ Loaded")
            init_embed_extended.set_field_at(1, name="Extensions", value="⌛ Loading...")

    elif update_type == "extensions":
        if len(value) == 0:
            init_embed_extended.set_field_at(1, name="Extensions", value="✅ Loaded")
        else:
            value = ', '.join(value)
            init_embed_extended.set_field_at(1, name="Extensions", value="⚠ Failed")
            init_embed_extended.add_field(name="Extensions failed", value=value, inline="False")
        init_embed_extended.set_field_at(2, name="Configs", value="⌛ Loading...")

    elif update_type == "configs":
        successful_load = True
        if len(bot.corrupt_configs) > 0:
            init_embed_extended.add_field(name="Configs failed", value="\n".join(bot.corrupt_configs), inline=False)
            successful_load = False
        if len(value) > 0:
            init_embed_extended.add_field(name="Configs not found", value="\n".join(value), inline=False)

        if successful_load:
            init_embed_extended.set_field_at(2, name="Configs", value="✅ Loaded")
        else:
            init_embed_extended.set_field_at(2, name="Configs", value="⚠ Failed")
        init_embed_extended.set_field_at(3, name="Database", value="⌛ Connecting...")

    elif update_type == "database":
        if value == DatabaseStatus.FAILED:
            init_embed_extended.set_field_at(3, name="Database", value="⚠ Failed")
        elif value == DatabaseStatus.CONNECTED:
            init_embed_extended.set_field_at(3, name="Database", value="✅ Connected")
        elif value == DatabaseStatus.UPGRADED:
            init_embed_extended.set_field_at(3, name="Database", value="✅ Upgraded")

    # TODO else clause?

    return init_embed_extended


async def load_extensions(bot):
    failed = []

    subfolders = [f.name for f in os.scandir('extensions') if f.is_dir()]
    for folder in subfolders:
        if "pycache" in folder:
            continue
        try:
            bot.load_extension("extensions." + folder + ".commands")
        except (commands.ExtensionNotFound, commands.ExtensionFailed, commands.NoEntryPointError) as exc:
            print(exc)
            failed.append(folder)
        except commands.ExtensionAlreadyLoaded as exc:
            print(exc)
    return failed


async def load_strings_and_values(bot):
    failed_strings = await strings.load_strings(bot)
    failed_strings.extend(await load_values(bot))
    return failed_strings


async def load_configs(bot):
    error_filenotfound_list = []

    for guild in bot.guilds:
        filename = str(guild.id)
        try:
            with open("config/" + filename + ".json", 'r') as json_file:
                try:
                    bot.config[filename] = json.load(json_file)
                except ValueError:
                    if filename not in bot.corrupt_configs:
                        bot.corrupt_configs.append(filename)
        except FileNotFoundError:
            error_filenotfound_list.append(filename)

    return error_filenotfound_list


async def connect_database(bot) -> DatabaseStatus:
    status = await db.check_if_db_up_to_date(bot)
    if status != DatabaseVersionStatus.NO_CONNECTION:
        if status == DatabaseVersionStatus.OUT_OF_DATE:
            await db.upgrade_database()
        await db.init_session(bot)
        # is not None if scoped session successfully created and checked
        if bot.db_session is not None:
            if status == DatabaseVersionStatus.UP_TO_DATE:
                return DatabaseStatus.CONNECTED
            else:
                return DatabaseStatus.UPGRADED
    return DatabaseStatus.FAILED


async def check_changelog(bot, init_embed, init_embed_extended):
    values = list(bot.values["changelog"].items())[-1]
    bot.version = values[0]
    embed_title = init_embed.title + " " + bot.version
    init_embed.title = embed_title
    init_embed_extended.title = embed_title

    if values[1].get("acknowledged") is False:
        description = "**Changes:**\n"
        description += values[1].get("changes")
        init_embed.description = description
        init_embed_extended.description = description
        values[1]["acknowledged"] = True
        await save_changelog(bot)

        return init_embed, init_embed_extended


async def send_startup_message(bot, init_embed):
    for guild_id in bot.config:
        if guild_id != "bot":
            await asyncio.sleep(1)
            guild = bot.get_guild(int(guild_id))
            channel = guild.get_channel(bot.config[guild_id]["essential_channels"]["bot_channel"])
            await channel.send(embed=init_embed)
