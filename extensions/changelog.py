import asyncio
import json
from datetime import date

import discord
from discord.ext import commands

from components import strings as s
from components.amadeusMenu import AmadeusMenu
from components.amadeusPrompt import AmadeusPrompt


class Changelog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='changelog')
    async def changelog(self, ctx, version: str = None):
        if version is None:
            pass

    @commands.command(name='addchangelog')
    @commands.is_owner()
    async def addchangelog(self, ctx):
        string_version_number = await s.get_string(ctx, "changelog", "version_number")
        string_changes = await s.get_string(ctx, "changelog", "changes")

        # ask for version number
        version_number = await self.__ask_for_version_number(ctx, string_version_number)
        if version_number is None:
            return

        # ask for changes
        changes = await self.__ask_for_changes(ctx, string_changes)
        if changes is None:
            return

        # ask if correct
        selection = await self.__ask_for_confirmation(ctx, string_version_number, string_changes, version_number, changes)
        if selection is None or selection == 1:
            await self.__show_result(ctx, False)
            return

        # if user selected yes, add to changelog and save to json file
        await self.__add_to_changelog(version_number, changes)
        await self.__save_changelog()
        await self.__show_result(ctx, True)

    async def __ask_for_version_number(self, ctx, string_version_number):
        prompt = AmadeusPrompt(self.bot, string_version_number.string)
        await prompt.set_user_specific(True)
        result = await prompt.show_prompt(ctx, 120)
        if result.input is None:
            await prompt.show_result(ctx)
        else:
            await result.message.delete()
        return result.input

    async def __ask_for_changes(self, ctx, string_changes):
        prompt = AmadeusPrompt(self.bot, string_changes.string)
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
        self.bot.changelog.setdefault(version_number, {})
        self.bot.changelog.get(version_number).setdefault("date", str(date.today()))
        self.bot.changelog.get(version_number).setdefault("acknowledged", False)
        self.bot.changelog.get(version_number).setdefault("changes", changes)

    async def __save_changelog(self):
        json_file = 'values/changelog.json'
        retries = 4
        while retries > 0:
            with open(json_file, 'w') as file:
                try:
                    json.dump(self.bot.changelog, file, indent=4)
                    return True
                except Exception as e:
                    print(e)
            retries -= 1
            await asyncio.sleep(1)

    async def __list_versions(self):
        embed = discord.Embed()

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
