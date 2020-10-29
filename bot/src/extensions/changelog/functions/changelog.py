import discord
from discord.ext.commands import Context

from components.amadeusPrompt import AmadeusPrompt
from helpers import strings as s, general


async def prepare_version_list_prompt(ctx: Context) -> AmadeusPrompt:
    string = await s.get_string("changelog", "version_history", ctx)
    prompt = AmadeusPrompt(ctx.bot, string.string)
    await prompt.set_user_specific(True)
    string = await s.get_string("changelog", "please_select", ctx)
    version_list = string.string + "\n\n"
    for version_number in ctx.bot.values["changelog"]:
        version_list += version_number + "\n"
    await prompt.set_description(version_list)
    return prompt


async def prepare_version_info_embed(ctx: Context, version: str) -> discord.Embed:
    embed = discord.Embed()
    if ctx.bot.values["changelog"].get(version) is None:
        string = await s.get_string("changelog", "does_not_exist", ctx)
        embed.title = string.string
    else:
        string = await s.get_string("changelog", "version", ctx)
        embed.title = string.string + " " + version
        date_changelog = await general.deep_get(ctx.bot.values["changelog"], version, "date")
        changes = await general.deep_get(ctx.bot.values["changelog"], version, "changes")
        string = await s.get_string("changelog", "release_date", ctx)
        embed.add_field(name=string.string, value=date_changelog)
        string = await s.get_string("changelog", "changes", ctx)
        embed.add_field(name=string.string, value=changes, inline=False)
    return embed