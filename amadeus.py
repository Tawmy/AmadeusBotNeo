import asyncio
import copy
import json
import platform

import asyncpg
import discord
from discord.ext import commands


def get_command_prefix(amadeus, message):
    try:
        return amadeus.config[message.guild.id]["command_prefix"]
    except KeyError:
        return "+"


bot = commands.Bot(command_prefix=get_command_prefix)

bot.config = {}
with open("config.json", 'r') as file:
    try:
        bot.config["bot"] = json.load(file)
        print("Configuration file loaded successfully")
    except ValueError as e:
        raise SystemExit(e)


@bot.event
async def on_ready():
    print("Connected to Discord")
    bot.app_info = await bot.application_info()

    # prepare init embeds for both main and all other servers
    init_embed, init_embed_extended = await prepare_init_embeds()
    init_message_extended = await send_init_message_extended(init_embed_extended)

    # await asyncio.sleep(1)  # debug

    # Load extensions and update extended init message
    failed_extensions = await load_extensions()
    await update_init_embed_extended("extensions", init_embed_extended, failed_extensions)
    await init_message_extended.edit(embed=init_embed_extended)

    # await asyncio.sleep(1)  # debug

    # TODO implement config loading
    # Load server configurations -> still skipped right now
    failed_configs = None
    await update_init_embed_extended("configs", init_embed_extended, failed_configs)
    await init_message_extended.edit(embed=init_embed_extended)

    # await asyncio.sleep(1)  # debug

    # Connect to database
    await connect_database(init_embed_extended, init_message_extended)

    # Check changelog, add to startup embed
    await check_changelog(init_embed, init_embed_extended)
    await init_message_extended.edit(embed=init_embed_extended)

    # Update guild table in database
    await update_guilds_table()

    # TODO send message on all servers
    channel = bot.get_channel(bot.config["bot"]["primary_server"]["main_channel_id"])
    await channel.send(embed=init_embed)


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
    init_embed_extended.add_field(name="Configs", value="⌛ Waiting...")
    init_embed_extended.add_field(name="Database", value="⌛ Waiting...")
    init_embed_extended.add_field(name="Discord.py", value=discord.__version__)
    init_embed_extended.add_field(name="Python", value=platform.python_version())
    init_embed_extended.add_field(name="ID", value=bot.app_info.id)

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
            init_embed_extended.add_field(name="Failed extensions", value=value)
        init_embed_extended.set_field_at(1, name="Configs", value="⌛ Loading...")

    elif update_type == "configs":
        init_embed_extended.set_field_at(1, name="Configs", value="✅ Loaded")
        init_embed_extended.set_field_at(2, name="Database", value="⌛ Connecting...")
        # TODO implement this

    elif update_type == "database":
        if value == 0:
            init_embed_extended.set_field_at(2, name="Database", value="⌛ Connecting...")
            init_embed_extended.set_footer(text="")
        elif value == 1:
            init_embed_extended.set_field_at(2, name="Database", value="✅ Connected")
        elif value == 2:
            init_embed_extended.set_field_at(2, name="Database", value="⚠ Failed")
            reconnect_msg = "Retrying database connection in "
            reconnect_msg += str(bot.config["bot"]["database"]["retry_timeout"])
            reconnect_msg += " seconds..."
            init_embed_extended.set_footer(text=reconnect_msg)

    # TODO else clause?

    return init_embed_extended


async def load_extensions():
    failed = []
    for extension in bot.config["bot"]["extensions"]["list"]:
        try:
            bot.load_extension(bot.config["bot"]["extensions"]["directory"] + "." + extension)
        except (discord.DiscordException, ModuleNotFoundError):
            failed.append(extension)
    return failed


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
        except asyncio.futures.TimeoutError:
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


print("Connecting to Discord...")
bot.run(bot.config["bot"]["token"], bot=True, reconnect=True)
