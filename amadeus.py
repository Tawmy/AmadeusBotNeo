import asyncio
import json
import platform

import asyncpg
import discord
from discord.ext import commands


def get_command_prefix():
    return "+"
    # TODO check database for prefix


bot = commands.Bot(command_prefix=get_command_prefix())

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
    init_embed_extended = await update_init_embed_extended("extensions", init_embed_extended, failed_extensions)
    await init_message_extended.edit(embed=init_embed_extended)

    # await asyncio.sleep(1)  # debug

    # TODO implement config loading
    # Load server configurations -> still skipped right now
    failed_configs = None
    init_embed_extended = await update_init_embed_extended("configs", init_embed_extended, failed_configs)
    await init_message_extended.edit(embed=init_embed_extended)

    # await asyncio.sleep(1)  # debug

    # Connect to database
    await connect_database(init_embed_extended, init_message_extended)

    # TODO send message on all servers


async def prepare_init_embeds():
    init_embed = discord.Embed()
    init_embed.title = bot.app_info.name
    init_embed.set_thumbnail(url="https://i.imgur.com/fvMdvyu.png")

    init_embed_extended = init_embed
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


print("Connecting to Discord...")
bot.run(bot.config["bot"]["token"], bot=True, reconnect=True)
