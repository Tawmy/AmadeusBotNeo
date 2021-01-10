import os
import sys
import json
from distutils.util import strtobool

import discord
from discord.ext import commands

from components import exceptions as ex
from helpers import strings, general, checks, startup
from helpers.strings import InsertPosition


def get_command_prefix(amadeus, message):
    try:
        return amadeus.config[str(message.guild.id)]["general"]["command_prefix"]
    except (KeyError, AttributeError):
        return "!"


intents = discord.Intents.all()
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)

bot = commands.Bot(command_prefix=get_command_prefix, intents=intents, allowed_mentions=allowed_mentions)
bot.dev_session = bool(strtobool(os.environ["DEV"]))
bot.ready = False
bot.corrupt_configs = []
bot.app_info = None
bot.database_pool = None
bot.values = {}
bot.config = {}


with open("values/config.json", 'r') as file:
    try:
        bot.config["bot"] = json.load(file)
        print("Configuration file loaded successfully")
    except ValueError as e:
        raise SystemExit(e)


@bot.check
async def global_check(ctx):
    # entire global check in its own helper
    return await checks.global_check(ctx, bot)


@bot.event
async def on_ready():
    bot.ready = False
    print("Connected to Discord")
    bot.app_info = await bot.application_info()

    # entire startup sequence in its own helper
    await startup.startup_sequence(bot)


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
        if embed is not None:
            await ctx.send(embed=embed)


async def prepare_command_error_embed(ctx, message):
    embed = discord.Embed()
    if hasattr(message.original, "text"):
        embed.title = message.original.text
    else:
        print(message, file=sys.stderr)
        return None
    if hasattr(message.original, "code") and message.original.code == 50013:
        string = await strings.get_string("amadeus", "exception_forbidden", ctx)
        values = [ctx.channel.mention, ctx.author.mention, ctx.command.name]
        string_combination = await strings.insert_into_string(values, string.list)
        embed.description = string_combination.string_combined
    return embed


async def prepare_command_error_embed_custom(ctx, message, error_config=None):
    embed = discord.Embed()
    ex_string = await strings.get_exception_strings(ctx, type(message).__name__)

    # if exception in strings, use that, otherwise show exception itself
    if not ex_string.successful:
        enabled_status = await general.deep_get(bot.config, str(ctx.guild.id), "general", "enabled")
        # TODO remove this bit once CommandNotFound handled differently
        if enabled_status is not True and ex_string.name == "CommandNotFound":
            return None
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
            if error_config.get("hide_whitelist_roles") is not True:
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

with open("/run/secrets/bot-token") as token_file:
    token = token_file.read()

if token == "":
    print("Could not read token file")
else:
    print("Connecting to Discord...")
    bot.run(token, bot=True, reconnect=True)
