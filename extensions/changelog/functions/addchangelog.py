import asyncio
import json
from datetime import date

import discord
from discord.ext.commands import Context

from components.amadeusMenu import AmadeusMenu
from components.amadeusPrompt import AmadeusPrompt
from helpers.strings import String
from helpers import strings as s


async def ask_for_input(ctx: Context, string: String) -> str:
    prompt = AmadeusPrompt(ctx.bot, string.string)
    await prompt.set_user_specific(True)
    result = await prompt.show_prompt(ctx, 120)
    if result.input is None:
        await prompt.show_result(ctx)
    else:
        await result.message.delete()
    return result.input


async def ask_for_confirmation(ctx: Context, string_version_number: String, string_changes: String, version_number: str, changes: str) -> int:
    string = await s.get_string(ctx, "changelog", "save")
    menu = AmadeusMenu(ctx.bot, string.string)
    await menu.set_user_specific(True)
    await menu.add_option("Yes")
    await menu.add_option("No")
    await menu.add_field(string_version_number.string, version_number)
    await menu.add_field(string_changes.string, changes, False)
    result = await menu.show_menu(ctx, 120)
    if result.reaction_index is None:
        await menu.show_result(ctx)
    else:
        await result.message.delete()
    return result.reaction_index


async def add_to_changelog(ctx, version_number: str, changes: str):
    ctx.bot.values["changelog"].setdefault(version_number, {})
    ctx.bot.values["changelog"].get(version_number).setdefault("date", str(date.today()))
    ctx.bot.values["changelog"].get(version_number).setdefault("acknowledged", False)
    ctx.bot.values["changelog"].get(version_number).setdefault("changes", changes)


async def show_result(ctx: Context, added: bool):
    embed = discord.Embed()
    if added:
        string = await s.get_string(ctx, "changelog", "added")
    else:
        string = await s.get_string(ctx, "changelog", "not_added")
    embed.title = string.string
    await ctx.send(embed=embed)


async def save_changelog(bot):
    json_file = 'values/changelog.json'
    retries = 4
    while retries > 0:
        with open(json_file, 'w') as file:
            try:
                json.dump(bot.values["changelog"], file, indent=4)
                return True
            except Exception as e:
                print(e)
        retries -= 1
        await asyncio.sleep(1)
