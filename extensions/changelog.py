import asyncio
import json
from datetime import date

import discord
from discord.ext import commands

from helpers import strings as s, general
from components.amadeusMenu import AmadeusMenu
from components.amadeusPrompt import AmadeusPrompt, AmadeusPromptStatus


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


class Changelog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='changelog')
    async def changelog(self, ctx, version: str = None):
        result = None
        if version is None:
            # if no version given, show version history and prompt for input
            prompt = await self.__prepare_version_list_prompt(ctx)
            result = await prompt.show_prompt(ctx, 120)
            # cancel by showing result if no input given
            if result.status != AmadeusPromptStatus.INPUT_GIVEN:
                await prompt.show_result(ctx)
            else:
                version = result.input
        # if version given either on command call or through prompt, check if exists and show details
        if version is not None:
            embed = await self.__prepare_version_info_embed(ctx, version)
            # if prompt shown previously, edit, otherwise send new message
            if result is not None and result.message is not None:
                await result.message.edit(embed=embed)
            else:
                await ctx.send(embed=embed)

    @commands.command(name='addchangelog')
    @commands.is_owner()
    async def addchangelog(self, ctx):
        string_version_number = await s.get_string(ctx, "changelog", "version_number")
        string_changes = await s.get_string(ctx, "changelog", "changes")

        # ask for version number
        version_number = await self.__ask_for_input(ctx, string_version_number)
        if version_number is None:
            return

        # ask for changes
        changes = await self.__ask_for_input(ctx, string_changes)
        if changes is None:
            return

        # ask if correct
        selection = await self.__ask_for_confirmation(ctx, string_version_number, string_changes, version_number, changes)
        if selection is None or selection == 1:
            await self.__show_result(ctx, False)
            return

        # if user selected yes, add to changelog and save to json file
        await self.__add_to_changelog(version_number, changes)
        await save_changelog(self.bot)
        await self.__show_result(ctx, True)

    async def __prepare_version_list_prompt(self, ctx):
        string = await s.get_string(ctx, "changelog", "version_history")
        prompt = AmadeusPrompt(self.bot, string.string)
        await prompt.set_user_specific(True)
        string = await s.get_string(ctx, "changelog", "please_select")
        version_list = string.string + "\n\n"
        for version_number in self.bot.values["changelog"]:
            version_list += version_number + "\n"
        await prompt.set_description(version_list)
        return prompt

    async def __prepare_version_info_embed(self, ctx, version) -> discord.Embed:
        embed = discord.Embed()
        if self.bot.values["changelog"].get(version) is None:
            string = await s.get_string(ctx, "changelog", "does_not_exist")
            embed.title = string.string
        else:
            string = await s.get_string(ctx, "changelog", "version")
            embed.title = string.string + " " + version
            date_changelog = await general.deep_get(self.bot.values["changelog"], version, "date")
            changes = await general.deep_get(self.bot.values["changelog"], version, "changes")
            string = await s.get_string(ctx, "changelog", "release_date")
            embed.add_field(name=string.string, value=date_changelog)
            string = await s.get_string(ctx, "changelog", "changes")
            embed.add_field(name=string.string, value=changes, inline=False)
        return embed

    async def __ask_for_input(self, ctx, string):
        prompt = AmadeusPrompt(self.bot, string.string)
        await prompt.set_user_specific(True)
        result = await prompt.show_prompt(ctx, 120)
        if result.input is None:
            await prompt.show_result(ctx)
        else:
            await result.message.delete()
        return result.input

    async def __ask_for_confirmation(self, ctx, string_version_number, string_changes, version_number, changes):
        string = await s.get_string(ctx, "changelog", "save")
        menu = AmadeusMenu(self.bot, string.string)
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

    async def __add_to_changelog(self, version_number, changes):
        self.bot.values["changelog"].setdefault(version_number, {})
        self.bot.values["changelog"].get(version_number).setdefault("date", str(date.today()))
        self.bot.values["changelog"].get(version_number).setdefault("acknowledged", False)
        self.bot.values["changelog"].get(version_number).setdefault("changes", changes)

    async def __show_result(self, ctx, added):
        embed = discord.Embed()
        if added:
            string = await s.get_string(ctx, "changelog", "added")
        else:
            string = await s.get_string(ctx, "changelog", "not_added")
        embed.title = string.string
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Changelog(bot))
