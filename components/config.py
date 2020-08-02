import json
import asyncio
import shlex
from dataclasses import dataclass
from distutils.util import strtobool
from enum import Enum

import discord
from discord.ext import commands
from discord.ext.commands import Context

from components import strings as s


class ConfigStatus(Enum):
    OTHER = 0
    OPTION_DOES_NOT_EXIST = 1
    CONVERSION_FAILED = 2
    NOT_IN_VALID_LIST = 3
    UNKNOWN_DATA_TYPE = 4
    NOT_VALID_FOR_DATA_TYPE = 5
    TEXT_CHANNEL_NOT_FOUND = 6
    ROLE_NOT_FOUND = 7
    PREPARATION_SUCCESSFUL = 10
    SAVE_SUCCESS = 11
    SAVE_FAIL = 12


class ReturnType(Enum):
    DEFAULT_VALUE = 0
    SERVER_VALUE = 1


class Datatype(Enum):
    CUSTOM = 0
    BOOLEAN = 1
    STRING = 2
    INTEGER = 3
    ROLE = 4
    TEXT_CHANNEL = 5
    VOICE_CHANNEL = 6


class InputType(Enum):
    ANY = 0
    AS_DATATYPE = 1
    AS_VALID_LIST = 2
    TO_BE_CONVERTED = 3


@dataclass
class Config:
    category: str
    name: str
    value: str = None
    return_type: ReturnType = None


@dataclass
class ValidInput:
    datatype: Datatype = None
    valid_list: list = None
    input_type: InputType = InputType.AS_DATATYPE


@dataclass
class PreparedInput:
    category: str
    name: str
    list: list = None
    status: ConfigStatus = None


async def load_values(bot: commands.bot) -> list:
    """Loads options and limits values. Returns list with filenames that failed.

    Parameters
    -----------
    bot: :class:`discord.ext.commands.bot`
        The bot object.
    """

    failed = []
    try:
        with open("values/options.json", 'r') as json_file:
            try:
                bot.options = json.load(json_file)
            except ValueError:
                failed.append("options")
    except FileNotFoundError as exc:
        failed.append(exc.filename)
    try:
        with open("values/limits.json", 'r') as json_file:
            try:
                bot.limits = json.load(json_file)
            except ValueError:
                failed.append("limits")
    except FileNotFoundError as exc:
        failed.append(exc.filename)
    try:
        with open("values/datatypes.json", 'r') as json_file:
            try:
                bot.datatypes = json.load(json_file)
            except ValueError:
                failed.append("datatypes")
    except FileNotFoundError as exc:
        failed.append(exc.filename)
    try:
        with open("values/changelog.json", 'r') as json_file:
            try:
                bot.changelog = json.load(json_file)
            except ValueError:
                failed.append("changelog")
    except FileNotFoundError as exc:
        failed.append(exc.filename)
    return failed


async def get_config(ctx: Context, category: str, name: str) -> Config:
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

    config = Config(category, name)
    config_value = ctx.bot.config.get(str(ctx.guild.id), {}).get(category, {}).get(name)
    if config_value is None:
        # TODO what if no default value
        default_value = await __get_default_config_value(ctx, category, name)
        # Save default value to config
        loop = asyncio.get_event_loop()
        loop.create_task(set_config(ctx, PreparedInput(category, name, [default_value])))
        config.value = default_value
        config.return_type = ReturnType.DEFAULT_VALUE
    else:
        config.value = config_value
        config.return_type = ReturnType.SERVER_VALUE
    return config


async def __get_default_config_value(ctx: Context, category: str, name: str) -> str:
    return ctx.bot.options.get(category, {}).get("list", {}).get(name, {}).get("default")


async def get_valid_input(ctx: Context, category: str, name: str) -> ValidInput:
    """Returns valid input for given config option.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        The invocation context.
    category: :class:`str`
        Category of the config option.
    name: :class:`str`
        Name of the config option.
    """

    valid_input = ValidInput()
    option = ctx.bot.options.get(category, {}).get("list", {}).get(name, {})
    data_type = option.get("data_type")
    valid_list = option.get("valid")

    datatype_dict = ctx.bot.datatypes.get(data_type)

    if valid_list is not None:
        valid_input.input_type = InputType.AS_VALID_LIST
        valid_input.valid_list = valid_list

    if data_type == "boolean":
        valid_input.datatype = Datatype.BOOLEAN
        valid_input.valid_list = datatype_dict.get("valid")
    if data_type == "string":
        valid_input.datatype = Datatype.STRING
        if valid_input.input_type != InputType.AS_VALID_LIST:
            valid_input.input_type = InputType.ANY
    if data_type == "role":
        valid_input.datatype = Datatype.ROLE
        valid_input.input_type = InputType.TO_BE_CONVERTED
        lang = await s.get_guild_language(ctx)
        valid_input.valid_list = [datatype_dict.get("name_descriptive", {}).get(lang)]
    if data_type == "channel":
        valid_input.datatype = Datatype.TEXT_CHANNEL
        valid_input.input_type = InputType.TO_BE_CONVERTED
        lang = await s.get_guild_language(ctx)
        valid_input.valid_list = [datatype_dict.get("name_descriptive", {}).get(lang)]

    return valid_input


async def set_config(ctx: Context, prepared_input: PreparedInput, do_save: bool = True):
    """Sets config value. First checks if it exists at all, then sets it and saves to config file.
    Please run the input through prepare_input first.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        The invocation context.
    prepared_input: :class:`PreparedInput`
        Prepared input from prepare_input()
    do_save: :class:`bool`
        Defines if value should be saved to file. Defaults to True.
    """

    await __convert_to_ids(prepared_input)
    if len(prepared_input.list) == 1:
        value = prepared_input.list[0]
    else:
        value = prepared_input.list
    if ctx.bot.options.get(prepared_input.category, {}).get("list", {}).get(prepared_input.name) is not None:
        ctx.bot.config[str(ctx.guild.id)].setdefault(prepared_input.category, {})[prepared_input.name] = value
        if do_save:
            save_successful = await save_config(ctx)
            prepared_input.status = ConfigStatus.SAVE_SUCCESS if save_successful else ConfigStatus.SAVE_FAIL
    else:
        prepared_input.status = ConfigStatus.OPTION_DOES_NOT_EXIST


async def set_default_config(ctx: Context, category: str, option: str) -> PreparedInput:
    default_value = await __get_default_config_value(ctx, category, option)
    prepared_input = PreparedInput(category, option, [default_value])
    await set_config(ctx, prepared_input)
    return prepared_input


async def __convert_to_ids(prepared_input: PreparedInput):
    for i, item in enumerate(prepared_input.list):
        if isinstance(item, (discord.TextChannel, discord.VoiceChannel, discord.Role)):
            prepared_input.list[i] = item.id


async def prepare_input(ctx: Context, category: str, name: str, user_input) -> PreparedInput:
    """Checks if input matches type specified in options list. Runs input converter when ctx specified.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        Invocation context.
    category: :class:`str`
        Category of the config option.
    name: :class:`str`
        Name of the config option.
    user_input:
        Input the user provided. Will be converted to str.
    """

    prepared_input = PreparedInput(category, name)

    # shlex to split string into multiple elements while keeping bracket terms intact
    if isinstance(user_input, str):
        user_input = shlex.split(user_input)
    elif isinstance(user_input, tuple):
        user_input = list(user_input)
    elif isinstance(user_input, (bool, int)):
        user_input = [str(user_input)]

    valid_input = await get_valid_input(ctx, category, name)

    prepared_input.list = []
    for user_input_item in user_input:
        if valid_input.input_type == InputType.AS_DATATYPE:
            if valid_input.datatype == Datatype.BOOLEAN:
                try:
                    prepared_input.list.append(bool(strtobool(user_input_item)))
                except ValueError:
                    prepared_input.status = ConfigStatus.NOT_VALID_FOR_DATA_TYPE
                    return prepared_input
        elif valid_input.input_type == InputType.ANY:
            if valid_input.datatype == Datatype.STRING:
                # TODO check if this needs str converter
                prepared_input.list.append(user_input_item)
        elif valid_input.input_type == InputType.AS_VALID_LIST:
            if user_input_item in valid_input.valid_list:
                prepared_input.list.append(user_input_item)
            else:
                prepared_input.status = ConfigStatus.NOT_IN_VALID_LIST
                return prepared_input
        elif valid_input.input_type == InputType.TO_BE_CONVERTED:
            if valid_input.datatype == Datatype.ROLE:
                try:
                    prepared_input.list.append(await commands.RoleConverter().convert(ctx, user_input_item))
                except commands.CommandError:
                    prepared_input.status = ConfigStatus.ROLE_NOT_FOUND
                    return prepared_input
            elif valid_input.datatype == Datatype.TEXT_CHANNEL:
                try:
                    prepared_input.list.append(await commands.TextChannelConverter().convert(ctx, user_input_item))
                except commands.CommandError:
                    prepared_input.status = ConfigStatus.TEXT_CHANNEL_NOT_FOUND
                    return prepared_input
    prepared_input.status = ConfigStatus.PREPARATION_SUCCESSFUL
    return prepared_input


async def save_config(ctx: Context,) -> bool:
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
                    return True
                except Exception as e:
                    print(e)
            retries -= 1
            await asyncio.sleep(1)
    return False
