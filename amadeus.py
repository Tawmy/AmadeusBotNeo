import sys

import asyncio
import copy
import json
import platform

import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands import Context

from components import exceptions as ex
from helpers import strings, config, general, checks
from helpers.strings import InsertPosition
from extensions.changelog import save_changelog


def get_command_prefix(amadeus, message):
    try:
        return amadeus.config[str(message.guild.id)]["general"]["command_prefix"]
    except (KeyError, AttributeError):
        return "!"


bot = commands.Bot(command_prefix=get_command_prefix)
bot.ready = False
bot.corrupt_configs = []
bot.app_info = None
bot.database_pool = None
bot.values = {}
bot.config = {}


with open("config/bot.json", 'r') as file:
    try:
        bot.config["bot"] = json.load(file)
        print("Configuration file loaded successfully")
    except ValueError as e:
        raise SystemExit(e)


@bot.check
async def global_check(ctx):
    return await checks.global_check(ctx, bot)


@bot.event
async def on_ready():
    bot.ready = False
    print("Connected to Discord")
    bot.app_info = await bot.application_info()

    # prepare init embeds for both main and all other servers
    init_embed, init_embed_extended = await prepare_init_embeds()
    init_message_extended = await send_init_message_extended(init_embed_extended)

    if init_message_extended is not None:
        # Load values
        values_status = await load_strings_and_values()
        await update_init_embed_extended("values", init_embed_extended, values_status)
        await init_message_extended.edit(embed=init_embed_extended)

        # Stop bot if any value file could not be loaded
        if len(values_status) > 0:
            raise SystemExit()

        # Load extensions and update extended init message
        failed_extensions = await load_extensions()
        await update_init_embed_extended("extensions", init_embed_extended, failed_extensions)
        await init_message_extended.edit(embed=init_embed_extended)

        # Check changelog, add to startup embed
        await check_changelog(init_embed, init_embed_extended)

        # Load server configurations
        configs = await load_configs()
        await update_init_embed_extended("configs", init_embed_extended, configs)
        await init_message_extended.edit(embed=init_embed_extended)

        bot.ready = True

        # Connect to database
        await connect_database(init_embed_extended, init_message_extended)

        # Send startup message on all servers
        await send_startup_message(init_embed)


@bot.event
async def on_command_error(ctx, message):
    if isinstance(message, commands.CommandInvokeError):
        bot_channel_id = await general.deep_get(bot.config, str(ctx.guild.id), "essential_channels", "bot_channel")
        if bot_channel_id is not None:
            bot_channel = ctx.guild.get_channel(bot_channel_id)
            embed = await prepare_command_error_embed(ctx, message)
            if embed is not None:
                await bot_channel.send(embed=embed)
    else:
        error_config = None
        if ctx.guild is not None:
            error_config = await general.deep_get(bot.config, str(ctx.guild.id), "errors")
        if error_config is None:
            error_config = {}
        if isinstance(message, commands.CommandNotFound) and error_config.get("hide_invalid_errors"):
            return
        if isinstance(message, (ex.BotDisabled, ex.CategoryDisabled, ex.CommandDisabled)) and error_config.get(
                "hide_disabled_errors"):
            return
        if isinstance(message,
                      (ex.CommandNotWhitelistedChannel, ex.CommandBlacklistedChannel)) and error_config.get(
                "hide_channel_errors"):
            return
        if isinstance(message, (ex.CategoryNoWhitelistedRole, ex.CommandNoWhitelistedRole, ex.CategoryBlacklistedRole, ex.CommandBlacklistedRole)):
            if error_config.get("hide_role_errors"):
                return
        embed = await prepare_command_error_embed_custom(ctx, message, error_config)
        await ctx.send(embed=embed)


async def prepare_command_error_embed(ctx, message):
    embed = discord.Embed()
    if hasattr(message.original, "text"):
        embed.title = message.original.text
    else:
        print(message, file=sys.stderr)
        return None
    if hasattr(message.original, "code") and message.original.code == 50013:
        string = await strings.get_string(ctx, "amadeus", "exception_forbidden")
        values = [ctx.channel.mention, ctx.author.mention, ctx.command.name]
        string_combination = await strings.insert_into_string(values, string.list)
        embed.description = string_combination.string_combined
    return embed


async def prepare_command_error_embed_custom(ctx, message, error_config=None):
    embed = discord.Embed()
    ex_string = await strings.get_exception_strings(ctx, type(message).__name__)

    # if exception in strings, use that, otherwise show exception itself
    if not ex_string.successful:
        embed.title = str(message)
    else:
        embed.title = ex_string.message

        # TODO test these after the changes
        # TODO separate lines for stringcombination
        if isinstance(message, ex.BotNotReady):
            string_combination = await strings.insert_into_string([bot.app_info.name], ex_string.description, InsertPosition.LEFT)
            embed.description = string_combination.string_combined
        elif isinstance(message, ex.CorruptConfig):
            string_combination = await strings.insert_into_string([bot.app_info.name, ctx.guild.name, bot.app_info.name], ex_string.description, InsertPosition.LEFT)
            embed.description = string_combination.string_combined
        elif isinstance(message, ex.DatabaseNotConnected):
            string_combination = await strings.insert_into_string([bot.app_info.name], ex_string.description)
            embed.description = string_combination.string_combined
        elif isinstance(message, ex.NotGuildOwner):
            string_combination = await strings.insert_into_string([ctx.guild.owner.mention], ex_string.description)
            embed.description = string_combination.string_combined
        elif isinstance(message, ex.BotNotConfigured):
            string_combination = await strings.insert_into_string([bot.app_info.name, ctx.guild.owner.mention], ex_string.description, InsertPosition.LEFT)
            embed.description = string_combination.string_combined
        elif isinstance(message, ex.BotDisabled):
            string_combination = await strings.insert_into_string([bot.app_info.name], ex_string.description, InsertPosition.LEFT)
            embed.description = string_combination.string_combined
        elif isinstance(message, (ex.CategoryNoWhitelistedRole, ex.CommandNoWhitelistedRole)):
            if error_config.get("hide_whitelist_role") is not True:
                embed.description = await strings.append_roles(ex_string.description[0], message.roles)
            else:
                embed.description = ex_string.description[0]
        elif isinstance(message, (ex.CategoryBlacklistedRole, ex.CommandBlacklistedRole)):
            if error_config.get("hide_blacklist_role") is not True:
                embed.description = await strings.append_roles(ex_string.description[0], message.role)
            else:
                embed.description = ex_string.description[0]
        else:
            embed.description = ex_string.description[0]
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar_url_as(static_format="png"))
    return embed


async def prepare_init_embeds():
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


async def send_init_message_extended(init_message_extended):
    channel = bot.get_channel(bot.config["bot"]["primary_server"]["main_channel_id"])
    if channel is not None:
        try:
            return await channel.send(embed=init_message_extended)
        except discord.Forbidden:
            print("Missing permissions, cannot send message.")
    else:
        print("Main channel not found, please fix this immediately.")


async def update_init_embed_extended(update_type, init_embed_extended, value):
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


async def load_extensions():
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


async def load_strings_and_values():
    failed_strings = await strings.load_strings(bot)
    failed_strings.extend(await config.load_values(bot))
    return failed_strings


async def load_configs():
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


async def connect_database(init_embed_extended, init_message_extended):
    while bot.database_pool is None:
        try:
            bot.database_pool = await asyncpg.create_pool(host=bot.config["bot"]["database"]["ip"],
                                                          database=bot.config["bot"]["database"]["name"],
                                                          user=bot.config["bot"]["database"]["username"],
                                                          password=bot.config["bot"]["database"]["password"],
                                                          command_timeout=bot.config["bot"]["database"]["cmd_timeout"],
                                                          timeout=bot.config["bot"]["database"]["timeout"])
            await update_init_embed_extended("database", init_embed_extended, 1)
            await init_message_extended.edit(embed=init_embed_extended)
        except (asyncio.futures.TimeoutError, OSError):
            await update_init_embed_extended("database", init_embed_extended, 2)
            await init_message_extended.edit(embed=init_embed_extended)
            await asyncio.sleep(bot.config["bot"]["database"]["retry_timeout"])
            await update_init_embed_extended("database", init_embed_extended, 0)
            await init_message_extended.edit(embed=init_embed_extended)


async def check_changelog(init_embed, init_embed_extended):
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


async def send_startup_message(init_embed):
    if bot.config["bot"]["debug"] is False:
        for guild_id in bot.config:
            if guild_id != "bot":
                await asyncio.sleep(1)
                guild = bot.get_guild(int(guild_id))
                channel = guild.get_channel(bot.config[guild_id]["essential_channels"]["bot_channel"])
                await channel.send(embed=init_embed)


print("Connecting to Discord...")
bot.run(bot.config["bot"]["token"], bot=True, reconnect=True)
