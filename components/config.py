import json
import asyncio
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
        """Returns value of config item specified. Returns default value if not set.

        Parameters
        -----------
        ctx: :class:`discord.ext.commands.Context`
            The invocation context.
        category: :class:`str`
            Category of the config option.
        name: :class:`str`
            Name of the config option.
        """

        config_value = ctx.bot.config.get(str(ctx.guild.id), {}).get(category, {}).get(name)
        if config_value is None:
            default_value = await self.__get_default_config_value(category, name)
            # Save default value to config
            loop = asyncio.get_event_loop()
            loop.create_task(self.set_config(ctx, category, name, default_value))
            return default_value
        return config_value

    async def __get_default_config_value(self, category, name):
        return self.options.get(category, {}).get("list", {}).get(name, {}).get("default")

    async def get_valid_input(self, category, name):
        """Returns valid input for given config option.
        Returns None if input can by any string.

        Parameters
        -----------
        category: :class:`str`
            Category of the config option.
        name: :class:`str`
            Name of the config option.
        """

        option = self.options.get(category, {}).get("list", {}).get(name, {})
        valid_list = option.get("valid")
        if valid_list is not None:
            return valid_list
        data_type = option.get("data_type")

        if data_type in ["boolean", "channel", "role"]:
            return data_type
        return None

    async def set_config(self, ctx, category, name, value):
        """Sets config value. First checks if it exists at all, then sets it and saves to config file.
        Please run the input through prepare_input first.
        Returns True if set, false if not.

        Parameters
        -----------
        ctx: :class:`discord.ext.commands.Context`
            The invocation context.
        category: :class:`str`
            Category of the config option.
        name: :class:`str`
            Name of the config option.
        value: :class:`str`
            Value to set
        """

        if self.options.get(category, {}).get("list", {}).get(name) is not None:
            ctx.bot.config[str(ctx.guild.id)].setdefault(category, {})[name] = value
            if await self.save_config(ctx) is True:
                return True
        return False

    async def prepare_input(self, category, name, user_input, ctx=None):
        """Checks if input matches type specified in options list. Runs input converter when ctx specified.
        Returns converted input if data type (and input) conversion was/were successful.
        Returns False if data type conversion failed.
        Returns None if data type conversion was successful, but input conversion failed.

        Parameters
        -----------
        category: :class:`str`
            Category of the config option.
        name: :class:`str`
            Name of the config option.
        user_input: :class:`str`
            Input the user provided.
        ctx: :class:`discord.ext.commands.Context`
            Optional invocation context, triggers input conversion when set.
        """

        option = self.options.get(category, {}).get("list", {}).get(name, {})
        if option is not None:
            data_type = option.get("data_type")
            is_list = option.get("is_list")
            valid_list = option.get("valid")
            if data_type is not None and is_list is not None:
                if valid_list is not None and user_input not in valid_list:
                    return False
                user_input = await self.__prepare_data_type_conversion(data_type, is_list, user_input)
                if user_input is not None:
                    if ctx is not None:
                        return await self.__convert_input(ctx, data_type, user_input)
                    else:
                        return user_input
        return False

    async def __prepare_data_type_conversion(self, data_type, is_list, user_input):
        # TODO check against is_list
        if is_list:
            converted_list = []
            for entry in user_input:
                converted_list.append(await self.__convert_data_type(data_type, entry))
            return converted_list
        else:
            return await self.__convert_data_type(data_type, user_input)

    async def __convert_data_type(self, data_type, user_input):
        if data_type == "boolean":
            if user_input.lower() in ["true", "yes", "1"]:
                return True
            elif user_input.lower() in ["false", "no", "0"]:
                return False
        elif data_type in ["string", "channel", "role"]:
            return user_input
        return None

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
        return user_input

    async def save_config(self, ctx):
        """Saves config of guild from ctx to json file

        Parameters
        -----------
        ctx: :class:`discord.ext.commands.Context`
            Invocation context, needed to determine guild.
        """
        if ctx.guild is not None:
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
