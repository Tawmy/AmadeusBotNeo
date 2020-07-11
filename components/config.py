import json
import asyncio
import shlex
from enum import Enum

from discord.ext import commands
from discord.ext.commands import Context


class ConfigStatus(Enum):
    OTHER = 0
    OPTION_DOES_NOT_EXIST = 1
    CONVERSION_FAILED = 2
    NOT_IN_VALID_LIST = 3
    UNKNOWN_DATA_TYPE = 4
    NOT_VALID_FOR_DATA_TYPE = 5
    TEXT_CHANNEL_NOT_FOUND = 6
    ROLE_NOT_FOUND = 7
    SAVE_SUCCESS = 10
    SAVE_FAIL = 11


async def load_values(bot: commands.bot):
    failed = []
    try:
        with open("values/options.json", 'r') as json_file:
            try:
                bot.options = json.load(json_file)
            except ValueError:
                failed.append("options")
        with open("values/limits.json", 'r') as json_file:
            try:
                bot.limits = json.load(json_file)
            except ValueError:
                failed.append("limits")
    except FileNotFoundError as exc:
        failed.append(exc.filename)
    return failed


async def get_config(ctx: Context, category: str, name: str) -> str:
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
        # TODO what if no default value
        default_value = await __get_default_config_value(ctx, category, name)
        # Save default value to config
        loop = asyncio.get_event_loop()
        loop.create_task(set_config(ctx, category, name, default_value))
        return default_value
    return config_value


async def __get_default_config_value(ctx: Context, category: str, name: str) -> str:
    return ctx.bot.options.get(category, {}).get("list", {}).get(name, {}).get("default")


async def get_valid_input(ctx: Context, category: str, name: str):
    """Returns valid input for given config option.
    Returns None if input can be any string.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        The invocation context.
    category: :class:`str`
        Category of the config option.
    name: :class:`str`
        Name of the config option.
    """

    option = ctx.bot.options.get(category, {}).get("list", {}).get(name, {})
    valid_list = option.get("valid")
    if valid_list is not None:
        return valid_list
    data_type = option.get("data_type")

    if data_type in ["boolean", "channel", "role"]:
        return data_type
    return None


async def set_config(ctx: Context, category: str, name: str, value: str):
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

    if ctx.bot.options.get(category, {}).get("list", {}).get(name) is not None:
        ctx.bot.config[str(ctx.guild.id)].setdefault(category, {})[name] = value
        return await save_config(ctx)
    return ConfigStatus.OPTION_DOES_NOT_EXIST


async def prepare_input(ctx: Context, category: str, name: str, user_input: str):
    """Checks if input matches type specified in options list. Runs input converter when ctx specified.
    Returns converted input if data type (and input) conversion was/were successful.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        Invocation context.
    category: :class:`str`
        Category of the config option.
    name: :class:`str`
        Name of the config option.
    user_input: :class:`str`
        Input the user provided.
    """

    option = ctx.bot.options.get(category, {}).get("list", {}).get(name, {})

    # shlex to split string into multiple elements while keeping bracket terms intact
    if isinstance(user_input, str):
        user_input = shlex.split(user_input)
    elif isinstance(user_input, tuple):
        user_input = list(user_input)

    if option is not None:
        if option.get("is_list"):
            for i, item in enumerate(user_input):
                checked_input = await __check_and_convert_input(option, item, ctx)
                if isinstance(checked_input, ConfigStatus):
                    return checked_input
                else:
                    user_input[i] = checked_input
            return user_input
        else:
            return await __check_and_convert_input(option, user_input[0], ctx)
    return ConfigStatus.OPTION_DOES_NOT_EXIST


async def __check_and_convert_input(option: str, user_input: str, ctx: Context):
    data_type = option.get("data_type")
    valid_list = option.get("valid")
    if valid_list is not None and user_input not in valid_list:
        return ConfigStatus.NOT_IN_VALID_LIST
    user_input_dt = await __convert_data_type(data_type, user_input)
    if isinstance(user_input_dt, ConfigStatus):
        converted_input = await __convert_input(ctx, data_type, user_input_dt)
        return converted_input
    else:
        return user_input_dt


async def __convert_data_type(data_type: str, user_input: str):
    if data_type == "boolean":
        if user_input.lower() in ["true", "yes", "1"]:
            return True
        elif user_input.lower() in ["false", "no", "0"]:
            return False
        return ConfigStatus.NOT_VALID_FOR_DATA_TYPE
    return user_input


async def __convert_input(ctx: Context, data_type: str, user_input: str):
    if data_type == "channel":
        try:
            return await commands.TextChannelConverter().convert(ctx, user_input)
        except commands.CommandError:
            return ConfigStatus.TEXT_CHANNEL_NOT_FOUND
    elif data_type == "role":
        try:
            return await commands.RoleConverter().convert(ctx, user_input)
        except commands.CommandError:
            return ConfigStatus.ROLE_NOT_FOUND
    return user_input


async def save_config(ctx: Context):
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
            with open(json_file, 'w') as file:
                try:
                    json.dump(ctx.bot.config[str(ctx.guild.id)], file, indent=4)
                    return ConfigStatus.SAVE_SUCCESS
                except Exception as e:
                    print(e)
            retries -= 1
            await asyncio.sleep(1)
    return ConfigStatus.SAVE_FAIL
