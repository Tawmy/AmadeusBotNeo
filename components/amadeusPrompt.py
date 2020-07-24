import asyncio
import discord

from dataclasses import dataclass
from components.enums import AmadeusPromptStatus
from components import strings as s


@dataclass
class AmadeusPromptResult:
    status: AmadeusPromptStatus = AmadeusPromptStatus.NEW
    message: discord.message = None
    input: str = None


class AmadeusPrompt:
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
        """Sets the author of the amadeusPrompt.

        Parameters
        -----------
        name: :class:`str`
            The name of the author.
        url: :class:`str`
            An optional url.
        icon_url: :class:`str`
            An optional icon url
        """

        self.__embed.set_author(name=name, url=url, icon_url=icon_url)

    async def set_title(self, title):
        self.__embed.title = title

    async def set_description(self, description):
        self.__embed.description = description

    async def append_description(self, description):
        """Appends to description.

        Parameters
        -----------
        description: :class:`str`
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
        """Sets if the prompt should be usable by one speficic user only.
        Defaults to context author if user is not speficied.

        Parameters
        -----------
        is_user_specific: :class:`bool`
            Should prompt be user specific?.
        user: :class:`discord.User`
            Optional user the prompt should be accessible by.
        """

        self.__is_user_specific = is_user_specific
        if user is not None:
            self.__specified_user = user

    async def set_cancel_string(self, cancel_string):
        self.__cancel_string = cancel_string

    async def show_prompt(self, ctx, timeout_seconds, message=None):
        """Displays the amadeusPrompt and waits for user input. Edits message if specified.
        Returns AmadeusPromptResult object.

        Parameters
        -----------
        ctx: :class:`discord.ext.commands.Context`
            The invocation context.
        timeout_seconds: :class:`int`
            Timeout in seconds.
        message: :class:`discord.Message`
            Optional message. This will be edited if specified.
        """

        await self.__prepare_footer(ctx)
        if message is None:
            self.__result.message = await ctx.send(embed=self.__embed)
        else:
            await message.edit(embed=self.__embed)
            self.__result.message = message
        self.__result.status = AmadeusPromptStatus.SHOWN
        await self.__await_user_input(ctx, timeout_seconds)
        return self.__result

    async def show_result(self, ctx):
        """Edits menu to show result.

        Parameters
        -----------
        ctx: :class:`discord.ext.commands.Context`
            The invocation context.
        """

        self.__embed = discord.Embed()
        string = None

        if self.__result.status == AmadeusPromptStatus.INPUT_GIVEN:
            string = await s.get_string(ctx, s.String("amadeusPromptStatus", "INPUT_GIVEN"))
        elif self.__result.status == AmadeusPromptStatus.TIMEOUT:
            string = await s.get_string(ctx, s.String("amadeusPromptStatus", "TIMEOUT"))
        elif self.__result.status == AmadeusPromptStatus.CANCELLED:
            string = await s.get_string(ctx, s.String("amadeusPromptStatus", "CANCELLED"))
        elif self.__result.status == AmadeusPromptStatus.SHOWN:
            string = await s.get_string(ctx, s.String("amadeusPromptStatus", "SHOWN"))
        elif self.__result.status == AmadeusPromptStatus.NEW:
            string = await s.get_string(ctx, s.String("amadeusPromptStatus", "NEW"))
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
                avatar = self.__specified_user.avatar_url_as(static_format="png")
            else:
                text = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png")
            text += " | "
        text += "Type \"" + self.__cancel_string + "\" to cancel"
        self.__embed.set_footer(text=text, icon_url=avatar)

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
