import json
import asyncio
import shlex
from distutils.util import strtobool

import discord
from discord.ext import commands
from discord.ext.commands import Context

from helpers import strings as s, general
from extensions.config.dataclasses import PreparedInput, ReturnType, ValidInput, Datatype, Config, InputType, ConfigStatus


async def load_values(bot: commands.bot) -> list:
    """
    Loads options, limits, datatypes, and changelog from values directory.
    Returns list with filenames that failed.

    Parameters
    -----------
    bot: discord.ext.commands.bot
        The bot object.
    """
    values = ["options", "limits", "datatypes", "changelog"]
    failed = []
    for value in values:
        try:
            with open("values/" + value + ".json", 'r') as json_file:
                try:
                    bot.values[value] = json.load(json_file)
                except ValueError:
                    failed.append(value)
        except FileNotFoundError as exc:
            failed.append(exc.filename)
    return failed


async def get_config(ctx: Context, category: str, name: str) -> Config:
    """
    Returns value of config item specified for the guild from context.
    Returns default value if not set.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        The invocation context.
    category: str
        Category of the config option.
    name: str
        Name of the config option.
    """
    config = Config(category, name)
    config_value = await general.deep_get(ctx.bot.config, str(ctx.guild.id), category, name)
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
    return await general.deep_get_type(str, ctx.bot.values["options"], category, "list", name, "default")


async def get_valid_input(ctx: Context, category: str, name: str) -> ValidInput:
    """
    Checks what type of input and if applicable which specific input must be provided. (eg ["en", "de"] for language)
    Returns ValidInput for given config option.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        The invocation context.
    category: str
        Category of the config option.
    name: str
        Name of the config option.
    """
    valid_input = ValidInput()
    option = await general.deep_get_type(dict, ctx.bot.values["options"], category, "list", name)
    data_type = option.get("data_type")
    valid_list = option.get("valid")

    datatype_dict = ctx.bot.values["datatypes"].get(data_type)

    if valid_list is not None:
        valid_input.input_type = InputType.AS_VALID_LIST
        valid_input.valid_list = valid_list

    if data_type is not None:
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
            valid_input.valid_list = [await general.deep_get(datatype_dict, "name_descriptive", lang)]
        if data_type == "channel":
            valid_input.datatype = Datatype.TEXT_CHANNEL
            valid_input.input_type = InputType.TO_BE_CONVERTED
            lang = await s.get_guild_language(ctx)
            valid_input.valid_list = [await general.deep_get(datatype_dict, "name_descriptive", lang)]
    return valid_input


async def set_config(ctx: Context, prepared_input: PreparedInput, do_save: bool = True):
    """
    Sets config value. First checks if it exists at all, then sets it and saves to config file.
    !!! Please run the input through prepare_input first !!!

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        The invocation context.
    prepared_input: PreparedInput
        Prepared input from prepare_input()
    do_save: Optional[bool]
        Defines if value should be saved to file. Defaults to True.
    """
    await __convert_to_ids(prepared_input)
    if len(prepared_input.list) == 1:
        value = prepared_input.list[0]
    else:
        value = prepared_input.list
    if await general.deep_get(ctx.bot.values["options"], prepared_input.category, "list", prepared_input.name) is not None:
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
    """
    Checks if input matches type specified in options list.
    Eg checks if valid channel/role, or if given input is part of the option's valid_list.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context.
    category: str
        Category of the config option.
    name: str
        Name of the config option.
    user_input:
        Input the user provided. Can be str, tuple of strings, bool, or int.
    """

    prepared_input = PreparedInput(category, name)

    user_input = await __convert_input_to_list(user_input)
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
            await __discord_converter(ctx, valid_input, prepared_input, user_input_item)
            if prepared_input.status in [ConfigStatus.ROLE_NOT_FOUND, ConfigStatus.TEXT_CHANNEL_NOT_FOUND]:
                return prepared_input

    prepared_input.status = ConfigStatus.PREPARATION_SUCCESSFUL
    return prepared_input


async def save_config(ctx: Context,) -> bool:
    """
    Saves config of guild from ctx to json file.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context, needed to determine guild.
    """
    if ctx.guild is not None:
        json_file = 'config/' + str(ctx.guild.id) + '.json'
        save_status = False
        retries = 4
        while save_status is False and retries > 0:
            file = open(json_file, 'w')
            try:
                json.dump(ctx.bot.config[str(ctx.guild.id)], file, indent=4)
                save_status = True
            except Exception as e:
                print(e)
                await asyncio.sleep(1)
            finally:
                file.close()
            retries -= 1
        return True if save_status is True else False
    return False


async def __convert_input_to_list(user_input) -> list:
    # shlex to split string into multiple elements while keeping bracket terms intact
    if isinstance(user_input, str):
        return shlex.split(user_input)
    elif isinstance(user_input, tuple):
        return list(user_input)
    elif isinstance(user_input, (bool, int)):
        return [str(user_input)]


async def __discord_converter(ctx, valid_input: ValidInput, prepared_input: PreparedInput, user_input_item: str):
    if valid_input.datatype == Datatype.ROLE:
        try:
            prepared_input.list.append(await commands.RoleConverter().convert(ctx, user_input_item))
        except commands.CommandError:
            prepared_input.status = ConfigStatus.ROLE_NOT_FOUND
    elif valid_input.datatype == Datatype.TEXT_CHANNEL:
        try:
            prepared_input.list.append(await commands.TextChannelConverter().convert(ctx, user_input_item))
        except commands.CommandError:
            prepared_input.status = ConfigStatus.TEXT_CHANNEL_NOT_FOUND
