import json
from dataclasses import dataclass
from enum import Enum

from discord.ext import commands
from discord.ext.commands import Context


class ReturnType(Enum):
    DEFAULT_LANGUAGE = 0
    SERVER_LANGUAGE = 1


class InsertPosition(Enum):
    LEFT = 0
    RIGHT = 1


@dataclass
class String:
    category: str
    name: str
    successful: bool = False
    return_type: ReturnType = None
    string: str = None
    list: list = None


@dataclass
class ExceptionString:
    name: str
    successful: bool = False
    return_type: ReturnType = None
    message: str = None
    description: list = None


@dataclass
class OptionStrings:
    successful: bool = False
    name: str = None
    description: str = None


@dataclass
class StringCombination:
    strings_source: list
    strings_target: list
    position: InsertPosition = None
    successful: bool = False
    string_combined: str = None


async def load_strings(bot: commands.bot) -> list:
    bot.default_language = bot.config["bot"].get("default_language", "en")
    failed = []
    try:
        with open("values/strings.json", 'r') as json_file:
            try:
                bot.strings = json.load(json_file)
            except ValueError:
                failed.append("strings")
        with open("values/exceptions.json", 'r') as json_file:
            try:
                bot.exception_strings = json.load(json_file)
            except ValueError:
                failed.append("exceptions")
    except FileNotFoundError as exc:
        failed.append(exc.filename)
    return failed


async def get_string(ctx: Context, string: String) -> String:
    """Gets string.

    Parameters
    -----------
    ctx: :class:`Context`
        Context
    string: :class:`String`
        String dataclass. Category and name must be provided.
    """

    lang = await get_language(ctx, string)
    returned_string = ctx.bot.strings.get(string.category, {}).get(string.name, {}).get(lang)
    # Get string in default language if nothing found for specified one
    if returned_string is None and lang != ctx.bot.default_language:
        returned_string = ctx.bot.strings.get(string.category, {}).get(string.name, {}).get(ctx.bot.default_language)
    if isinstance(returned_string, list):
        string.list = returned_string
    else:
        string.string = returned_string
    if string.list is not None or string.string is not None:
        string.successful = True
    return string


async def get_language(ctx: Context, string: String = None) -> str:
    """Gets language for guild.
    Returns default language if run outside of a guild or if guild has no language set.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        Invocation context, needed to determine guild.
    string: :class:`String`
        Optional String dataclass. If provided, return type is set.
    """

    if ctx.guild is not None:
        lang = ctx.bot.config.get(str(ctx.guild.id), {}).get("general", {}).get("language")
    else:
        lang = None
    if lang is not None:
        if string is not None:
            string.return_type = ReturnType.SERVER_LANGUAGE
        return lang
    else:
        if string is not None:
            string.return_type = ReturnType.DEFAULT_LANGUAGE
        return ctx.bot.default_language


async def get_exception_strings(ctx: Context, ex_string: ExceptionString) -> ExceptionString:
    """Gets strings for exception.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        Invocation context, needed to determine guild.
    ex_string: :class:`ExceptionString`
        ExceptionString dataclass. Name must be provided.
    """

    lang = await get_language(ctx)
    exception = ctx.bot.exception_strings.get(ex_string.name)
    if exception is not None:
        ex_string.successful = True
        ex_string.message = exception.get("message", {}).get(lang)
        # Get string in default language if nothing found for specified one
        if ex_string.message is None and lang != ctx.bot.default_language:
            ex_string.message = exception.get("message", {}).get(ctx.bot.default_language)
        description = exception.get("description", {}).get(lang)
        # Get string in default language if nothing found for specified one
        if description is None and lang != ctx.bot.default_language:
            description = exception.get("description", {}).get(ctx.bot.default_language)
        ex_string.description = [description] if isinstance(description, str) else description
    return ex_string


async def extract_config_option_strings(ctx: Context, option_dict: dict) -> OptionStrings:
    """Extracts config strings from submitted configuration option dictionary.

    Parameters
    -----------
    ctx: :class:`discord.ext.commands.Context`
        Invocation context, needed to determine guild.
    option_dict: :class:`dict`
        Dictionary to extract strings from.
    """

    option_strings = OptionStrings()
    lang = await get_language(ctx)
    option_strings.name = option_dict.get("name", {}).get(lang)
    # Get string in default language if nothing found for specified on
    if option_strings.name is None and lang != ctx.bot.default_language:
        option_strings.name = option_dict.get("name", {}).get(ctx.bot.default_language)
    option_strings.description = option_dict.get("description", {}).get(lang)
    # Get string in default language if nothing found for specified on
    if option_strings.description is None and lang != ctx.bot.default_language:
        option_strings.description = option_dict.get("description", {}).get(ctx.bot.default_language)
    if option_strings.name is not None and option_strings.description is not None:
        option_strings.successful = True
    return option_strings


async def insert_into_string(string_combination: StringCombination) -> StringCombination:
    """Inserts values into string. Length of values must be one shorter than strings.
    If same length, position must be speficied.

    Parameters
    -----------
    string_combination: :class:`StringCombination`
        StringCombination object.
    """

    # TODO allow for insertion without automatic space between combined elements

    if len(string_combination.strings_target) == len(string_combination.strings_source) + 1:
        string_combination.successful = True
        string_combination.string_combined = string_combination.strings_target[0]
        for i, value in enumerate(string_combination.strings_source):
            string_combination.string_combined += " "
            string_combination.string_combined += value
            string_combination.string_combined += " "
            string_combination.string_combined += string_combination.strings_target[i + 1]
    elif len(string_combination.strings_target) == len(string_combination.strings_source):
        string_combination.string_combined = ""
        if string_combination.position == InsertPosition.LEFT:
            string_combination.successful = True
            for i, value in enumerate(string_combination.strings_source):
                string_combination.string_combined += value
                string_combination.string_combined += " "
                string_combination.string_combined += string_combination.strings_target[i]
                string_combination.string_combined += " "
        elif string_combination.position == InsertPosition.RIGHT:
            string_combination.successful = True
            for i, string in enumerate(string_combination.strings_target):
                string_combination.string_combined += string
                string_combination.string_combined += " "
                string_combination.string_combined += string_combination.strings_source[i]
                string_combination.string_combined += " "
    return string_combination


async def append_roles(string: str, roles: list) -> str:
    """Adds newlines and appends roles to string.
    I actually hate this.

    Parameters
    -----------
    string: :class:`str`
        String to append to.
    roles: :class:`list`
        List of strings to append to string.
    """

    roles_string = string + "\n\n**"
    if type(roles) is list:
        roles_string += '**, **'.join(roles)
    else:
        roles_string += roles
    roles_string += "**"
    return roles_string
