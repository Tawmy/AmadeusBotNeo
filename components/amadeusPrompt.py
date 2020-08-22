import asyncio
from enum import Enum

import discord

from dataclasses import dataclass

from discord import Message
from discord.ext.commands import Bot, Context

from components.amadeusInput import AmadeusInput
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


class AmadeusPrompt(AmadeusInput):
    """
    Prompt awaiting text by user as input.

    This prompt can be customised using:
    - set_cancel_string: Sets a custom cancel string - this is "cancel" by default

    This prompt can be controlled using:
    - show_prompt: Shows prompt and awaits input for specified number of seconds
    - show_result: Edits prompt and shows result
    """
    # TODO change bot to ctx for consistency (in menu too)
    def __init__(self, bot: Bot, title: str):
        """
        Parameters
        ------------
        bot: discord.ext.commands.bot
            Bot object
        title: str
            Title of the prompt
        """
        super().__init__()
        self.bot = bot
        self.__cancel_string = "cancel"

        self.embed.title = title

        self.__result = AmadeusPromptResult()

    async def set_cancel_string(self, cancel_string: str):
        self.__cancel_string = cancel_string

    async def show_prompt(self, ctx: Context, timeout_seconds: int, message: Message = None) -> AmadeusPromptResult:
        """
        Displays the amadeusPrompt and waits for user input. Edits message if specified.

        Parameters
        -----------
        ctx: discord.ext.commands.Context
            The invocation context.
        timeout_seconds: int
            Timeout in seconds.
        message: Message, optional
            Optional message. This will be edited if specified.
        """
        await self.__prepare_footer(ctx)
        await self.__add_cancel_string_to_footer(ctx)
        if message is None:
            self.__result.message = await ctx.send(embed=self.embed)
        else:
            await message.edit(embed=self.embed)
            self.__result.message = message
        self.__result.status = AmadeusPromptStatus.SHOWN
        await self.__await_user_input(ctx, timeout_seconds)
        return self.__result

    async def show_result(self, ctx: Context):
        """
        Edits menu to show result.

        Parameters
        -----------
        ctx: Context
            The invocation context.
        """
        self.embed = discord.Embed()
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
            self.embed.title = string.string
        await self.__prepare_footer(ctx)
        self.__result.message = await self.__result.message.edit(embed=self.embed)

    async def __prepare_footer(self, ctx: Context):
        text = ""
        avatar = ""
        if self.is_user_specific:
            if self.specified_user is not None:
                text = self.specified_user.display_name
                avatar = self.specified_user.avatar_url_as(static_format="png", size=64)
            else:
                text = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png", size=64)
        self.embed.set_footer(text=text, icon_url=avatar)

    async def __add_cancel_string_to_footer(self, ctx: Context):
        """
        Make sure to always run __prepare_footer before this one, otherwise icon_url may cause exception.

        Parameters
        -----------
        ctx: Context
            The invocation context.
        """
        current_text = self.embed.footer.text
        if current_text is not None and len(current_text) > 0:
            current_text += " | "
        string = await s.get_string(ctx, "prompt", "cancel")
        string_combination = await s.insert_into_string(["\"" + self.__cancel_string + "\""], string.list)
        current_text += string_combination.string_combined
        self.embed.set_footer(text=current_text, icon_url=self.embed.footer.icon_url)

    async def __await_user_input(self, ctx: Context, timeout_seconds: int):
        def check(user_message):
            result = False
            if user_message.channel is ctx.channel:
                if self.is_user_specific:
                    if self.specified_user is not None:
                        if user_message.author == self.specified_user:
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
