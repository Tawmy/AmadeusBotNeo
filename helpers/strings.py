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


async def load_strings(bot: commands.Bot) -> list:
    """
    Loads strings and exceptions from values directory.
    Returns list with filenames that failed.

    Parameters
    -----------
    bot: discord.ext.commands.bot
        The bot object.
    """
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


async def get_string(ctx: Context, category: str, name: str) -> String:
    """
    Gets string. First tries to get string in server language, falls back to default language if not found.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context. Needed to determine guild language.
    category: str
        Category of string.
    name: str
        Name of string.
    """

    string = String(category, name)
    lang = await get_guild_language(ctx, string)
    style = await get_guild_style(ctx)
    returned_string = ctx.bot.strings.get(string.category, {}).get(string.name, {}).get(lang, {}).get(style)
    # Get string in default language if nothing found for specified one
    # TODO possibly fall back to default style before falling back to default lang
    if returned_string is None and lang != ctx.bot.default_language:
        returned_string = ctx.bot.strings.get(string.category, {}).get(string.name, {}).get(ctx.bot.default_language, {}).get(style)
    if isinstance(returned_string, list):
        string.list = returned_string
    else:
        string.string = returned_string
    if string.list is not None or string.string is not None:
        string.successful = True
    return string


async def get_guild_language(ctx: Context, string: String = None) -> str:
    """
    Gets language for guild.
    Returns default language if run outside of a guild or if guild has no language set.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context, needed to determine guild.
    string: Optional[str]
        Optional String dataclass. If provided, return type in this dataclass object is set.
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
        default_language = ctx.bot.values["options"].get("general", {}).get("list", {}).get("language", {}).get("default")
        return default_language if default_language is not None else ctx.bot.default_language


async def get_guild_style(ctx: Context) -> str:
    """
    Gets language style for guild.
    Returns default style if run outside of a guild or if guild has no language set.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context, needed to determine guild.
    """

    if ctx.guild is not None:
        style = ctx.bot.config.get(str(ctx.guild.id), {}).get("general", {}).get("style")
    else:
        style = None
    if style is not None:
        return style
    else:
        # TODO change default to amadeus once those have been created
        return ctx.bot.values["options"]["general"]["list"]["style"]["default"]


async def get_exception_strings(ctx: Context, ex_name: str) -> ExceptionString:
    """
    Gets strings for exception.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context, needed to determine guild.
    ex_name: str
        Name of Exception.
    """

    ex_string = ExceptionString(ex_name)
    lang = await get_guild_language(ctx)
    style = await get_guild_style(ctx)
    exception = ctx.bot.exception_strings.get(ex_string.name)
    if exception is not None:
        ex_string.successful = True
        # TODO possibly fall back to default style before falling back to default lang
        ex_string.message = exception.get("message", {}).get(lang, {}).get(style)
        # Get string in default language if nothing found for specified one
        if ex_string.message is None and lang != ctx.bot.default_language:
            ex_string.message = exception.get("message", {}).get(ctx.bot.default_language, {}).get(style)
        description = exception.get("description", {}).get(lang, {}).get(style)
        # Get string in default language if nothing found for specified one
        if description is None and lang != ctx.bot.default_language:
            description = exception.get("description", {}).get(ctx.bot.default_language, {}).get(style)
        ex_string.description = [description] if isinstance(description, str) else description
    return ex_string


async def extract_config_option_strings(ctx: Context, option_dict: dict) -> OptionStrings:
    """
    Extracts config strings from submitted configuration option dictionary.

    Parameters
    -----------
    ctx: discord.ext.commands.Context
        Invocation context, needed to determine guild.
    option_dict: dict
        Dictionary to extract strings from.
    """

    option_strings = OptionStrings()
    lang = await get_guild_language(ctx)
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


async def insert_into_string(strings_source: list, strings_target: list, position: InsertPosition = None) -> StringCombination:
    """
    Inserts values into string. Length of strings_source is ideally one less than length of strings_target.
    If same length, position must be speficied.

    Parameters
    -----------
    strings_source: list
        List of strings to be inserted into strings_target.
    strings_target: list
        List of strings strings_source should be inserted into.
    position: Optional[InsertionPosition]
        Enum required if length of strings_source = strings_target.
        Sets whether strings_source are to be inserted on the left or right.
    """

    # TODO allow for insertion without automatic space between combined elements

    string_combination = StringCombination(strings_source, strings_target, position)
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
    """
    Adds newlines and appends roles to string.
    I actually hate this.

    Parameters
    -----------
    string: str
        String to append to.
    roles: list
        List of strings to append to string.
    """

    roles_string = string + "\n\n**"
    if isinstance(roles, list):
        roles_string += '**, **'.join(roles)
    else:
        roles_string += roles
    roles_string += "**"
    return roles_string
