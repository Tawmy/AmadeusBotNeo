import copy
import json
import platform

import asyncio
import asyncpg
import discord
from discord.ext import commands

from extensions.changelog import save_changelog
from helpers import strings, config


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
            init_embed_extended.set_field_at(3, name="Database", value="🛑 Cancelled")
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
        if value == 0:
            init_embed_extended.set_field_at(3, name="Database", value="⌛ Connecting...")
            init_embed_extended.set_footer(text="")
        elif value == 1:
            init_embed_extended.set_field_at(3, name="Database", value="✅ Connected")
        elif value == 2:
            init_embed_extended.set_field_at(3, name="Database", value="⚠ Failed")
            reconnect_msg = "Retrying database connection in "
            reconnect_msg += str(bot.config["bot"]["database"]["retry_timeout"])
            reconnect_msg += " seconds..."
            init_embed_extended.set_footer(text=reconnect_msg)

    # TODO else clause?

    return init_embed_extended


async def load_extensions(bot):
    failed = []
    for extension in bot.config["bot"]["extensions"]:
        try:
            bot.load_extension("extensions." + extension)
        except (commands.ExtensionNotFound, commands.ExtensionFailed, commands.NoEntryPointError) as exc:
            print(exc)
            failed.append(extension)
        except commands.ExtensionAlreadyLoaded as exc:
            print(exc)
    return failed


async def load_strings_and_values(bot):
    failed_strings = await strings.load_strings(bot)
    failed_strings.extend(await config.load_values(bot))
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


async def connect_database(bot, init_embed_extended, init_message_extended):
    while bot.database_pool is None:
        try:
            bot.database_pool = await asyncpg.create_pool(host=bot.config["bot"]["database"]["ip"],
                                                          database=bot.config["bot"]["database"]["name"],
                                                          user=bot.config["bot"]["database"]["username"],
                                                          password=bot.config["bot"]["database"]["password"],
                                                          command_timeout=bot.config["bot"]["database"]["cmd_timeout"],
                                                          timeout=bot.config["bot"]["database"]["timeout"])
            await update_init_embed_extended(bot, "database", init_embed_extended, 1)
            await init_message_extended.edit(embed=init_embed_extended)
        except (asyncio.exceptions.TimeoutError, OSError):
            await update_init_embed_extended(bot, "database", init_embed_extended, 2)
            await init_message_extended.edit(embed=init_embed_extended)
            await asyncio.sleep(bot.config["bot"]["database"]["retry_timeout"])
            await update_init_embed_extended(bot, "database", init_embed_extended, 0)
            await init_message_extended.edit(embed=init_embed_extended)


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
    if bot.config["bot"]["debug"] is False:
        for guild_id in bot.config:
            if guild_id != "bot":
                await asyncio.sleep(1)
                guild = bot.get_guild(int(guild_id))
                channel = guild.get_channel(bot.config[guild_id]["essential_channels"]["bot_channel"])
                await channel.send(embed=init_embed)