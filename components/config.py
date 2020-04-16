import json
import asyncio


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
