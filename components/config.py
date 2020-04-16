import json
import asyncio
import discord
from discord.ext import commands


class Config:
    def __init__(self, bot_config):
        self.default_language = bot_config.get("default_language", "en")
        self.options = {}
        self.limits = {}

    async def load_values(self):
        failed = []
        try:
            with open("values/options.json", 'r') as json_file:
                try:
                    self.options = json.load(json_file)
                except ValueError:
                    failed.append("options")
            with open("values/limits.json", 'r') as json_file:
                try:
                    self.limits = json.load(json_file)
                except ValueError:
                    failed.append("limits")
        except FileNotFoundError as exc:
            failed.append(exc.filename)
        return failed

    async def get_config(self, ctx, category, name):
        config_value = ctx.bot.config.get(str(ctx.guild.id), {}).get(category, {}).get(name)
        if config_value is None:
            return self.__get_default_config_value(category, name)

    async def __get_default_config_value(self, category, name):
        return self.options.get(category, {}).get(name, {}).get("default")

    async def set_config(self, ctx, category, name, value):
        if self.options.get(category, {}).get("list", {}).get(name) is not None:
            ctx.bot.config[str(ctx.guild.id)].setdefault(category, {})[name] = value
            if await self.save_config(ctx) is True:
                return True
        return False

    async def check_input(self, category, name, user_input, ctx=None):
        option = self.options.get(category, {}).get("list", {}).get(name, {})
        if option is not None:
            data_type = option.get("data_type")
            is_list = option.get("is_list")
            if data_type is not None and is_list is not None:
                if type(user_input) == await self.__convert_data_type(data_type):
                    if ctx is not None:
                        return await self.__convert_input(ctx, data_type, user_input)
                    else:
                        return True
        return False

    async def __convert_data_type(self, data_type):
        if data_type == "boolean":
            return bool
        elif data_type in ["string", "channel", "role"]:
            return str

    async def __convert_input(self, ctx, data_type, user_input):
        if data_type == "channel":
            try:
                return await commands.TextChannelConverter().convert(ctx, user_input)
            except commands.CommandError:
                return None
        elif data_type == "role":
            try:
                return await commands.RoleConverter().convert(ctx, user_input)
            except commands.CommandError:
                return None
        return True

    async def save_config(self, ctx):
        json_file = 'config/' + str(ctx.guild.id) + '.json'
        save_status = False
        retries = 4
        while save_status is False and retries > 0:
            with open(json_file, 'w+') as file:
                try:
                    json.dump(ctx.bot.config[str(ctx.guild.id)], file)
                    return True
                except Exception as e:
                    print(e)
            retries -= 1
            await asyncio.sleep(25e-2)
        return False
