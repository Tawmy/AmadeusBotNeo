from discord.ext import commands
from discord.ext.commands import Context

from helpers import strings as s, messages
from components.amadeusPrompt import AmadeusPromptStatus
from extensions.changelog.functions import changelog, addchangelog


class Changelog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='changelog')
    async def changelog(self, ctx: Context, version: str = None):
        result = None
        if version is None:
            # if no version given, show version history and prompt for input
            prompt = await changelog.prepare_version_list_prompt(ctx)
            result = await prompt.show_prompt(ctx, 120)
            # cancel by showing result if no input given
            if result.status != AmadeusPromptStatus.INPUT_GIVEN:
                await prompt.show_result(ctx)
            else:
                version = result.input
        # if version given either on command call or through prompt, check if exists and show details
        if version is not None:
            embed = await changelog.prepare_version_info_embed(ctx, version)
            # if prompt shown previously, edit, otherwise send new message
            if result is not None and result.message is not None:
                await messages.edit(result.message, embed)
            else:
                await messages.reply(ctx, embed)

    @commands.command(name='addchangelog')
    @commands.is_owner()
    async def addchangelog(self, ctx: Context):
        string_version_number = await s.get_string(ctx, "changelog", "version_number")
        string_changes = await s.get_string(ctx, "changelog", "changes")

        # ask for version number
        version_number = await addchangelog.ask_for_input(ctx, string_version_number)
        if version_number is None:
            return

        # ask for changes
        changes = await addchangelog.ask_for_input(ctx, string_changes)
        if changes is None:
            return

        # ask if correct
        selection = await addchangelog.ask_for_confirmation(ctx, string_version_number, string_changes, version_number, changes)
        if selection is None or selection == 1:
            await addchangelog.show_result(ctx, False)
            return

        # if user selected yes, add to changelog and save to json file
        await addchangelog.ack_all_entries(ctx)
        await addchangelog.add_to_changelog(ctx, version_number, changes)
        await addchangelog.save_changelog(ctx.bot)
        await addchangelog.show_result(ctx, True)


def setup(bot):
    bot.add_cog(Changelog(bot))
