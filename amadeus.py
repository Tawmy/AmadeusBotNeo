import json

import discord
from discord.ext import commands


def get_command_prefix():
    return "+"
    # TODO check database for prefix


bot = commands.Bot(command_prefix=get_command_prefix())


print("Loading configuration file...")

bot.config = {}
with open("config.json", 'r') as file:
    try:
        bot.config["config"] = json.load(file)
        print("Configuration file loaded successfully")
    except ValueError as e:
        print(e)

print(bot.config)

for cog in bot.config["config"]["cogs"]:
    try:
        bot.load_extension(bot.config["config"]["cogs_directory"] + "." + cog)
    except (discord.ClientException, ModuleNotFoundError):
        print('Failed to load extension ' + cog)