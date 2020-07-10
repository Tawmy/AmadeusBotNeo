import json
from dataclasses import dataclass
from enum import Enum
from discord.ext.commands import Context


class ReturnType(Enum):
    DEFAULT_LANGUAGE = 0
    SERVER_LANGUAGE = 1


@dataclass
class String:
    category: str
    name: str
    return_type: ReturnType = None
    value: str = None


async def load_strings(bot):
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
        String dataclass
    """

    lang = await get_language(ctx, string)
    string.value = ctx.bot.strings.get(string.category, {}).get(string.name, {}).get(lang)
    # Get string in default language if nothing found for specified one
    if string.value is None and lang != ctx.bot.default_language:
        string = ctx.bot.strings.get(string.category, {}).get(string.name, {}).get(ctx.bot.default_language)
    return string


async def get_language(ctx: Context, string: String) -> str:
    if ctx.guild is not None:
        lang = ctx.bot.config.get(str(ctx.guild.id), {}).get("general", {}).get("language")
    else:
        lang = None
    if lang is not None:
        string.return_type = ReturnType.SERVER_LANGUAGE
        return lang
    else:
        string.return_type = ReturnType.DEFAULT_LANGUAGE
        return ctx.bot.default_language
