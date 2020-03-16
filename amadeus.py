import asyncio
import json
import platform

import discord
from discord.ext import commands


def get_command_prefix():
    return "+"
    # TODO check database for prefix


bot = commands.Bot(command_prefix=get_command_prefix())

bot.config = {}
with open("config.json", 'r') as file:
    try:
        bot.config["config"] = json.load(file)
        print("Configuration file loaded successfully")
    except ValueError as e:
        raise SystemExit(e)


@bot.event
async def on_ready():
    print("Connected to Discord")
    bot.app_info = await bot.application_info()

    # prepare init embeds for both main and all other servers
    init_embed, init_embed_extended = await prepare_init_messages()
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

    # TODO implement database connection
    # Connect to database -> still skipped right now
    database_status = None
    init_embed_extended = await update_init_embed_extended("database", init_embed_extended, database_status)
    await init_message_extended.edit(embed=init_embed_extended)


async def prepare_init_messages():
    init_embed = discord.Embed()
    if bool(bot.app_info.icon_url):
        init_embed.set_author(name=bot.app_info.name, icon_url=bot.app_info.icon_url)
    else:
        init_embed.set_author(name=bot.app_info.name)
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
    channel = bot.get_channel(bot.config["config"]["primary_server"]["main_channel_id"])
    if channel is not None:
        try:
            return await channel.send(embed=init_message_extended)
        except discord.Forbidden:
            print("Missing permissions, cannot send message.")
    else:
        print("Main channel not found, please fix this immediately.")


async def update_init_embed_extended(update_type, init_embed_extended, error_value):
    if update_type == "extensions":
        if len(error_value) == 0:
            init_embed_extended.set_field_at(0, name="Extensions", value="✅ Loaded")
        else:
            error_value = ', '.join(error_value)
            init_embed_extended.set_field_at(0, name="Extensions", value="⚠ Failed")
            init_embed_extended.add_field(name="Failed extensions", value=error_value)
        init_embed_extended.set_field_at(1, name="Configs", value="⌛ Loading...")

    elif update_type == "configs":
        init_embed_extended.set_field_at(1, name="Configs", value="✅ Loaded")
        init_embed_extended.set_field_at(2, name="Database", value="⌛ Connecting...")
        # TODO implement this

    elif update_type == "database":
        init_embed_extended.set_field_at(2, name="Database", value="✅ Connected")

    # TODO else clause?

    return init_embed_extended


async def load_extensions():
    failed = []
    for extension in bot.config["config"]["extensions"]["list"]:
        try:
            bot.load_extension(bot.config["config"]["extensions"]["directory"] + "." + extension)
        except (discord.DiscordException, ModuleNotFoundError):
            failed.append(extension)
    return failed


print("Connecting to Discord...")
bot.run(bot.config["config"]["bot"]["token"], bot=True, reconnect=True)
