import sys

import asyncio
import copy
import json
import platform

import asyncpg
import discord
from discord.ext import commands
from components import exceptions as ex, strings, config


def get_command_prefix(amadeus, message):
    try:
        return amadeus.config[str(message.guild.id)]["general"]["command_prefix"]
    except (KeyError, AttributeError):
        return "!"


bot = commands.Bot(command_prefix=get_command_prefix)
bot.ready = False
bot.corrupt_configs = []

bot.config = {}
with open("config/bot.json", 'r') as file:
    try:
        bot.config["bot"] = json.load(file)
        print("Configuration file loaded successfully")
    except ValueError as e:
        raise SystemExit(e)
bot.values = config.Config(bot.config["bot"])


@bot.check
async def global_check(ctx):
    if not bot.ready:
        raise ex.BotNotReady

    if ctx.command.name not in bot.config["bot"]["no_global_check"]:
        guild_config = bot.config.get(str(ctx.guild.id), {})

        # Is bot enabled on server? (set to True during setup)
        bot_status = guild_config.get("general", {}).get("enabled")
        if bot_status is None:
            if str(ctx.guild.id) in bot.corrupt_configs:
                raise ex.CorruptConfig
            else:
                raise ex.BotNotConfigured
        elif bot_status is False:
            raise ex.BotDisabled

        guild_config_cat = guild_config.get("limits", {}).get("categories")
        guild_config_com = guild_config.get("limits", {}).get("commands")
        moderator_skip_enabled = bot.config[str(ctx.guild.id)].get("general", {}).get("mods_override_limits", {})
        if discord.utils.get(ctx.author.roles, id=bot.config[str(ctx.guild.id)]["essential_roles"]["mod_role"]):
            user_is_moderator = True
        else:
            user_is_moderator = False

        if guild_config_cat is not None:
            # Is extension enabled on server?
            if guild_config_cat.get(ctx.command.cog_name, {}).get("enabled") is False:
                raise ex.CategoryDisabled

            if moderator_skip_enabled and user_is_moderator:
                pass
            # Do not check for extension role limits if command has role limits specified
            elif not await command_has_role_limits(ctx, guild_config_com):
                # Does the extension have role limits?
                wl = guild_config_cat.get(ctx.command.cog_name, {}).get("roles", {}).get("whitelist", [])
                bl = guild_config_cat.get(ctx.command.cog_name, {}).get("roles", {}).get("blacklist", [])
                result = await check_role_limits(ctx, wl, bl)
                if result[0] == 1:
                    raise ex.CategoryNoWhitelistedRole(result[1])
                elif result[0] == 2:
                    raise ex.CategoryBlacklistedRole(result[1])

        if guild_config_com is not None:
            # Is command enabled on the server?
            if guild_config_com.get(ctx.command.name, {}).get("enabled") is False:
                raise ex.CommandDisabled

            if moderator_skip_enabled and user_is_moderator:
                pass
            else:
                # Does the command have channel limits?
                wl = guild_config_com.get(ctx.command.name, {}).get("channels", {}).get("whitelist", [])
                bl = guild_config_com.get(ctx.command.name, {}).get("channels", {}).get("blacklist", [])
                if len(wl) > 0 and ctx.channel.id not in wl:
                    raise ex.CommandNotWhitelistedChannel
                if ctx.channel.id in bl:
                    raise ex.CommandBlacklistedChannel

                # Does the command have role limits?
                wl = guild_config_com.get(ctx.command.name, {}).get("roles", {}).get("whitelist", [])
                bl = guild_config_com.get(ctx.command.name, {}).get("roles", {}).get("blacklist", [])
                result = await check_role_limits(ctx, wl, bl)
                if result[0] == 1:
                    raise ex.CommandNoWhitelistedRole(result[1])
                if result[0] == 2:
                    raise ex.CommandBlacklistedRole(result[1])

        # TODO time limits

    return True


async def command_has_role_limits(ctx, guild_config_com):
    if guild_config_com is not None:
        wl = guild_config_com.get(ctx.command.name, {}).get("roles", {}).get("whitelist", [])
        bl = guild_config_com.get(ctx.command.name, {}).get("roles", {}).get("blacklist", [])
        return len(wl) + len(bl) > 0
    return False


async def check_role_limits(ctx, wl, bl):
    if len(wl) + len(bl) > 0:
        match = False
        for role in ctx.author.roles:
            # TODO check if this can throw exception if bl/wl is None
            if role.id in wl:
                match = True
            if role.id in bl:
                return [2, role]
        if len(wl) > 0 and match is False:
            role_list = []
            for role_id in wl:
                role_list.append(ctx.guild.get_role(role_id))
            return [1, role_list]
    return [0]


@bot.event
async def on_ready():
    bot.ready = False
    print("Connected to Discord")
    bot.app_info = await bot.application_info()

    # prepare init embeds for both main and all other servers
    init_embed, init_embed_extended = await prepare_init_embeds()
    init_message_extended = await send_init_message_extended(init_embed_extended)

    if init_message_extended is not None:
        # Load extensions and update extended init message
        failed_extensions = await load_extensions()
        await update_init_embed_extended("extensions", init_embed_extended, failed_extensions)
        await init_message_extended.edit(embed=init_embed_extended)

        # Load values
        values_status = await load_strings_and_values()
        await update_init_embed_extended("values", init_embed_extended, values_status)
        await init_message_extended.edit(embed=init_embed_extended)

        # Load server configurations
        configs = await load_configs()
        await update_init_embed_extended("configs", init_embed_extended, configs)
        await init_message_extended.edit(embed=init_embed_extended)

        bot.ready = True

        # Connect to database
        await connect_database(init_embed_extended, init_message_extended)

        # Check changelog, add to startup embed
        await check_changelog(init_embed, init_embed_extended)
        await init_message_extended.edit(embed=init_embed_extended)

        # Update guild table in database
        await update_guilds_table()

        # Send startup message on all servers
        await send_startup_message(init_embed)


@bot.event
async def on_command_error(ctx, message):
    if isinstance(message, commands.CommandInvokeError):
        bot_channel_id = bot.config.get(str(ctx.guild.id), {}).get("essential_channels", {}).get("bot_channel")
        if bot_channel_id is not None:
            bot_channel = ctx.guild.get_channel(bot_channel_id)
            embed = await prepare_command_error_embed(ctx, message)
            if embed is not None:
                await bot_channel.send(embed=embed)
    else:
        if ctx.guild is not None:
            error_config = bot.config.get(str(ctx.guild.id), {}).get("errors")
        else:
            error_config = None
        if error_config is not None:
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
        else:
            embed = await prepare_command_error_embed_custom(ctx, message)
        await ctx.send(embed=embed)


async def prepare_command_error_embed(ctx, message):
    embed = discord.Embed()
    if hasattr(message.original, "text"):
        embed.title = message.original.text
    else:
        print(message, file=sys.stderr)
        return None
    if hasattr(message.original, "code") and message.original.code == 50013:
        string_list = await bot.strings.get_string(ctx, "amadeus", "exception_forbidden")
        values = [ctx.channel.mention, ctx.author.mention, ctx.command.name]
        embed.description = await bot.strings.insert_into_string(string_list, values)
    return embed


async def prepare_command_error_embed_custom(ctx, message, error_config=None):
    embed = discord.Embed()
    exc_strings = await bot.strings.get_exception_strings(ctx, type(message).__name__)
    if exc_strings is None:
        embed.title = str(message)
    else:
        embed.title = exc_strings[0]

        if isinstance(message, ex.BotNotReady):
            embed.description = await bot.strings.insert_into_string(exc_strings[1], bot.app_info.name, "left")
        elif isinstance(message, ex.CorruptConfig):
            embed.description = await bot.strings.insert_into_string(exc_strings[1], [bot.app_info.name, ctx.guild.name, bot.app_info.name], "left")
        elif isinstance(message, ex.DatabaseNotConnected):
            embed.description = await bot.strings.insert_into_string(exc_strings[1], bot.app_info.name)
        elif isinstance(message, ex.NotGuildOwner):
            embed.description = await bot.strings.insert_into_string(exc_strings[1], ctx.guild.owner.mention)
        elif isinstance(message, ex.BotNotConfigured):
            embed.description = await bot.strings.insert_into_string(exc_strings[1], [bot.app_info.name, ctx.guild.owner.mention], "left")
        elif isinstance(message, ex.BotDisabled):
            embed.description = await bot.strings.insert_into_string(exc_strings[1], bot.app_info.name, "left")
        elif isinstance(message, (ex.CategoryNoWhitelistedRole, ex.CommandNoWhitelistedRole)):
            if error_config.get("hide_whitelist_role") is not True:
                embed.description = await bot.strings.append_roles(exc_strings[1], message.roles)
            else:
                embed.description = exc_strings[1]
        elif isinstance(message, (ex.CategoryBlacklistedRole, ex.CommandBlacklistedRole)):
            if error_config.get("hide_blacklist_role") is not True:
                embed.description = await bot.strings.append_roles(exc_strings[1], message.role)
            else:
                embed.description = exc_strings[1]
        else:
            embed.description = exc_strings[1]
    embed.set_footer(text=ctx.author.display_name, icon_url=ctx.author.avatar_url_as(static_format="png"))
    return embed


@bot.event
async def on_guild_join(guild):
    db_guilds = await request_guild_ids()

    in_database = False
    for db_guild in db_guilds:
        if db_guild["id"] == guild.id:
            in_database = True

    if in_database is False:
        await upsert_guild(guild)


async def request_guild_ids():
    sql = '''   SELECT id
                FROM guilds'''

    con = await bot.database_pool.acquire()
    try:
        return await con.fetch(sql)
    finally:
        await bot.database_pool.release(con)


async def upsert_guild(guild):
    sql = '''   INSERT INTO guilds (id, name)
                VALUES ($1::bigint, $2::text)
                ON CONFLICT (id)
                DO UPDATE SET id = $1::bigint, name = $2::text'''
    con = await bot.database_pool.acquire()
    try:
        await con.execute(sql, guild.id, guild.name)
    finally:
        await bot.database_pool.release(con)


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
    if update_type == "extensions":
        if len(value) == 0:
            init_embed_extended.set_field_at(0, name="Extensions", value="✅ Loaded")
        else:
            value = ', '.join(value)
            init_embed_extended.set_field_at(0, name="Extensions", value="⚠ Failed")
            init_embed_extended.add_field(name="Extensions failed", value=value, inline="False")
        init_embed_extended.set_field_at(1, name="Values", value="⌛ Loading...")

    elif update_type == "values":
        if len(value) > 0:
            init_embed_extended.add_field(name="Values failed", value="\n".join(value), inline=False)
            init_embed_extended.set_field_at(1, name="Values", value="⚠ Failed")
        else:
            init_embed_extended.set_field_at(1, name="Values", value="✅ Loaded")
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
        except (commands.ExtensionNotFound, commands.ExtensionFailed, commands.NoEntryPointError) as ex:
            print(ex)
            failed.append(extension)
        except commands.ExtensionAlreadyLoaded as ex:
            print(ex)
    return failed


async def load_strings_and_values():
    failed_strings = await strings.load_strings(bot)
    failed_strings.extend(await bot.values.load_values())
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
    bot.database_pool = None

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
    sql = '''   (SELECT id, version, changes, acknowledged
                FROM changelog
                WHERE acknowledged = false
                ORDER BY time
                LIMIT 1)
                
                UNION ALL
                
                (SELECT id, version, changes, acknowledged
                FROM changelog
                WHERE acknowledged = true
                ORDER BY time DESC
                LIMIT 1)
                '''

    con = await bot.database_pool.acquire()
    try:
        fields = await con.fetch(sql)
        bot.version = fields[0]["version"]
    finally:
        await bot.database_pool.release(con)

    embed_title = init_embed.title + " " + bot.version
    init_embed.title = embed_title
    init_embed_extended.title = embed_title

    if len(fields) > 0 and fields[0]["acknowledged"] is False:

        description = "**Changes:**\n"
        description += fields[0]["changes"]
        init_embed.description = description
        init_embed_extended.description = description

        sql = '''   UPDATE changelog
                    SET acknowledged = true
                    WHERE id = $1::integer'''

        con = await bot.database_pool.acquire()
        try:
            await con.execute(sql, fields[0]["id"])
        finally:
            await bot.database_pool.release(con)

        return init_embed, init_embed_extended


async def update_guilds_table():
    db_guilds = await request_guild_ids()

    db_guild_ids = []
    for db_guild in db_guilds:
        db_guild_ids.append(db_guild["id"])

    # Upsert only if not already in guild list provided by Discord API
    for bot_guild in bot.guilds:
        if bot_guild.id not in db_guild_ids:
            await upsert_guild(bot_guild)


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
