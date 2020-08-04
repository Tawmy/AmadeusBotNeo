import asyncio
from enum import Enum

import discord

from dataclasses import dataclass
from helpers import strings as s


class AmadeusPromptStatus(Enum):
    NEW = 0
    SHOWN = 1
    CANCELLED = 2
    TIMEOUT = 3
    INPUT_GIVEN = 4


@dataclass
class AmadeusPromptResult:
    status: AmadeusPromptStatus = AmadeusPromptStatus.NEW
    message: discord.message = None
    input: str = None


class AmadeusPrompt:
    """
    Prompt awaiting text by user as input.

    This menu can be customised using:
    - set_author: Set the embed author
    - set_title: Change the title of the prompt
    - set_description: Set the embed description
    - append_description: Append more text to the embed description
    - add_field: Add a field to the embed
    - set_user_specific: Sets if only one and optionally which user will be able to reply to the prompt
    - set_cancel_string: Sets a custom cancel string - this is "cancel" by default

    This menu can be controlled using:
    - show_prompt: Shows prompt and awaits input for specified number of seconds
    - show_result: Edits prompt and shows result

    Parameters
    ------------
    bot: discord.ext.commands.bot
        Bot object
    title: str
        Title of the prompt
    """
    # TODO change bot to ctx for consistency (in menu too)
    def __init__(self, bot, title):
        self.bot = bot
        self.__is_user_specific = False
        self.__specified_user = None
        self.__cancel_string = "cancel"

        self.__embed = discord.Embed()
        self.__embed.title = title

        self.__result = AmadeusPromptResult()

    async def set_author(self, name, url="", icon_url=""):
        """
        Sets the author of the amadeusPrompt.

        Parameters
        -----------
        name: str
            The name of the author.
        url: Optional[str]
            An optional url.
        icon_url: Optional[str]
            An optional icon url
        """
        self.__embed.set_author(name=name, url=url, icon_url=icon_url)

    async def set_title(self, title):
        self.__embed.title = title

    async def set_description(self, description):
        self.__embed.description = description

    async def append_description(self, description):
        """
        Appends to description.

        Parameters
        -----------
        description: str
            The string to append to the description.
        """
        if self.__embed.description is not None and len(self.__embed.description) > 0:
            self.__embed.description += description
        else:
            await self.set_description(description)

    async def add_field(self, name, description, inline=True):
        if name is not None and description is not None:
            self.__embed.add_field(name=name, value=description, inline=inline)

    async def set_user_specific(self, is_user_specific, user=None):
        """
        Sets if the prompt should be usable by one speficic user only.
        Defaults to context author if user is not speficied.

        Parameters
        -----------
        is_user_specific: bool
            Should prompt be user specific?.
        user: Optional[discord.User]
            Optional user the prompt should be accessible by.
        """
        self.__is_user_specific = is_user_specific
        if user is not None:
            self.__specified_user = user

    async def set_cancel_string(self, cancel_string):
        self.__cancel_string = cancel_string

    async def show_prompt(self, ctx, timeout_seconds, message=None) -> AmadeusPromptResult:
        """
        Displays the amadeusPrompt and waits for user input. Edits message if specified.

        Parameters
        -----------
        ctx: discord.ext.commands.Context
            The invocation context.
        timeout_seconds: int
            Timeout in seconds.
        message: Optional[discord.Message]
            Optional message. This will be edited if specified.
        """
        await self.__prepare_footer(ctx)
        await self.__add_cancel_string_to_footer(ctx)
        if message is None:
            self.__result.message = await ctx.send(embed=self.__embed)
        else:
            await message.edit(embed=self.__embed)
            self.__result.message = message
        self.__result.status = AmadeusPromptStatus.SHOWN
        await self.__await_user_input(ctx, timeout_seconds)
        return self.__result

    async def show_result(self, ctx):
        """
        Edits menu to show result.

        Parameters
        -----------
        ctx: discord.ext.commands.Context
            The invocation context.
        """
        self.__embed = discord.Embed()
        string = None

        if self.__result.status == AmadeusPromptStatus.INPUT_GIVEN:
            string = await s.get_string(ctx, "amadeusPromptStatus", "INPUT_GIVEN")
        elif self.__result.status == AmadeusPromptStatus.TIMEOUT:
            string = await s.get_string(ctx, "amadeusPromptStatus", "TIMEOUT")
        elif self.__result.status == AmadeusPromptStatus.CANCELLED:
            string = await s.get_string(ctx, "amadeusPromptStatus", "CANCELLED")
        elif self.__result.status == AmadeusPromptStatus.SHOWN:
            string = await s.get_string(ctx, "amadeusPromptStatus", "SHOWN")
        elif self.__result.status == AmadeusPromptStatus.NEW:
            string = await s.get_string(ctx, "amadeusPromptStatus", "NEW")
        if string is not None:
            self.__embed.title = string.string
        await self.__prepare_footer(ctx)
        self.__result.message = await self.__result.message.edit(embed=self.__embed)

    async def __prepare_footer(self, ctx):
        text = ""
        avatar = ""
        if self.__is_user_specific:
            if self.__specified_user is not None:
                text = self.__specified_user.display_name
                avatar = self.__specified_user.avatar_url_as(static_format="png", size=64)
            else:
                text = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png", size=64)
        self.__embed.set_footer(text=text, icon_url=avatar)

    async def __add_cancel_string_to_footer(self, ctx):
        """
        Make sure to always run __prepare_footer before this one, otherwise icon_url may cause exception.

        Parameters
        -----------
        ctx: discord.ext.commands.Context
            The invocation context.
        """
        current_text = self.__embed.footer.text
        if current_text is not None and len(current_text) > 0:
            current_text += " | "
        string = await s.get_string(ctx, "prompt", "cancel")
        string_combination = await s.insert_into_string(["\"" + self.__cancel_string + "\""], string.list)
        current_text += string_combination.string_combined
        self.__embed.set_footer(text=current_text, icon_url=self.__embed.footer.icon_url)

    async def __await_user_input(self, ctx, timeout_seconds):
        def check(user_message):
            result = False
            if user_message.channel is ctx.channel:
                if self.__is_user_specific:
                    if self.__specified_user is not None:
                        if user_message.author == self.__specified_user:
                            result = True
                    elif user_message.author == ctx.author:
                        result = True
                else:
                    result = True
            return result

        try:
            user_message = await self.bot.wait_for('message', timeout=timeout_seconds, check=check)
        except asyncio.TimeoutError:
            self.__result.status = AmadeusPromptStatus.TIMEOUT
        else:
            await user_message.delete()
            if user_message.content in [self.__cancel_string, "\"" + self.__cancel_string + "\""]:
                self.__result.status = AmadeusPromptStatus.CANCELLED
            else:
                self.__result.status = AmadeusPromptStatus.INPUT_GIVEN
                self.__result.input = user_message.content
