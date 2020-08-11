import asyncio
from enum import Enum

import discord

from dataclasses import dataclass

from discord import User, Message
from discord.ext.commands import Bot, Context

from helpers import strings as s


class AmadeusMenuStatus(Enum):
    NEW = 0
    SHOWN = 1
    CANCELLED = 2
    TIMEOUT = 3
    SELECTED = 4
    NO_OPTIONS = 5


@dataclass
class AmadeusMenuResult:
    status: AmadeusMenuStatus = AmadeusMenuStatus.NEW
    message: discord.message = None
    reaction_index: int = None
    reaction_emoji: str = None


@dataclass
class Option:
    name: str
    value: str


class AmadeusMenu:
    """
    Menu using Discord reaction to get user input.

    This menu must be configured using:
    - add_option: For each option you want the user to select from

    This menu can be customised using:
    - add_field: Add a field without adding it as an option
    - set_author: Set the embed author
    - set_title: Change the title of the menu
    - set_description: Set the embed description
    - set_footer_text: Define text to be shown in footer
    - append_description: Append more text to the embed description
    - set_user_specific: Sets if only one and optionally which user will be able to use the menu
    - set_clear_on_timeout: Sets if reactions will be cleared if menu times out
    - append_emoji: Adds more emoji the user will be able to select from as options

    This menu can be controlled using:
    - show_menu: Shows menu and awaits input for specified number of seconds
    - show_result: Edits menu and shows result
    """
    def __init__(self, bot: Bot, title: str):
        """
         Parameters
        ------------
        bot: Bot
            Discord bot object
        title: str
            Title of the menu
        """
        self.bot = bot
        self.__is_user_specific = False
        self.__clear_on_timeout = True
        self.__specified_user = None
        self.__footer_text = None

        self.__embed = discord.Embed()
        self.__embed.title = title

        self.__options = []
        self.__reaction_emoji = []

        self.__result = AmadeusMenuResult()

    async def add_option(self, name: str, description: str = None):
        if name is not None:
            self.__options.append(Option(name, description))

    async def add_field(self, name: str, description: str, inline: bool = True):
        if name is not None and description is not None:
            self.__embed.add_field(name=name, value=description, inline=inline)

    async def set_author(self, name: str, url: str = "", icon_url: str = ""):
        """
        Sets the author of the amadeusMenu.

        Parameters
        -----------
        name: str
            The name of the author.
        url: str, optional
            An optional url.
        icon_url: str, optional
            An optional icon url.
        """
        self.__embed.set_author(name=name, url=url, icon_url=icon_url)

    async def set_title(self, title: str):
        self.__embed.title = title

    async def set_description(self, description: str):
        self.__embed.description = description

    async def set_footer_text(self, text: str):
        self.__footer_text = text

    async def append_description(self, description: str):
        if self.__embed.description is not None and len(self.__embed.description) > 0:
            self.__embed.description += description
        else:
            await self.set_description(description)

    async def set_user_specific(self, is_user_specific: bool, user: User = None):
        """
        Sets if the menu should be usable by one speficic user only.
        Defaults to context author if user is not speficied.

        Parameters
        -----------
        is_user_specific: bool
            Should menu be user specific?
        user: User, optional
            Optional user the menu should be usable by.
        """
        self.__is_user_specific = is_user_specific
        if user is not None:
            self.__specified_user = user

    async def set_clear_on_timeout(self, clear_on_timeout: bool):
        """
        Sets if reactions should be removed on timeout.

        Parameters
        -----------
        clear_on_timeout: bool
            Should reactions be cleared on timeout?
        """
        self.__clear_on_timeout = clear_on_timeout

    async def append_emoji(self, emoji_list: list):
        for emoji in emoji_list:
            self.__reaction_emoji.append(emoji)

    async def show_menu(self, ctx: Context, timeout_seconds: int, message: Message = None) -> AmadeusMenuResult:
        """
        Displays the amadeusMenu and waits for user input. Edits message if specified.

        Parameters
        -----------
        ctx: discord.ext.commands.Context
            The invocation context.
        timeout_seconds: int
            Timeout in seconds.
        message: Message, optional
            Optional message. This will be edited if specified.
        """
        await self.__add_options(ctx)
        await self.__prepare_footer(ctx)
        if len(self.__reaction_emoji) == 0:
            self.__result.status = AmadeusMenuStatus.NO_OPTIONS
            return self.__result
        else:
            if message is None:
                message = await ctx.send(embed=self.__embed)
            else:
                await message.edit(embed=self.__embed)
            self.__result.status = AmadeusMenuStatus.SHOWN
            await self.__add_reactions(message)
            await self.__await_user_reaction(ctx, message, timeout_seconds)
            return self.__result

    async def show_result(self, ctx: Context):
        """
        Edits menu to show result.

        These are generic messages, you will most certainly want to write your own success messages.

        Parameters
        -----------
        ctx: Context
            The invocation context.
        """
        self.__embed = discord.Embed()
        string = None

        if self.__result.status == AmadeusMenuStatus.SELECTED:
            string = await s.get_string(ctx, "amadeusMenuStatus", "SELECTED")
        elif self.__result.status == AmadeusMenuStatus.TIMEOUT:
            string = await s.get_string(ctx, "amadeusMenuStatus", "TIMEOUT")
        elif self.__result.status == AmadeusMenuStatus.CANCELLED:
            string = await s.get_string(ctx, "amadeusMenuStatus", "CANCELLED")
        elif self.__result.status == AmadeusMenuStatus.SHOWN:
            string = await s.get_string(ctx, "amadeusMenuStatus", "SHOWN")
        elif self.__result.status == AmadeusMenuStatus.NEW:
            string = await s.get_string(ctx, "amadeusMenuStatus", "NEW")
        if string is not None:
            self.__embed.title = string.string
        await self.__prepare_footer(ctx)
        self.__result.message = await self.__result.message.edit(embed=self.__embed)

    async def __prepare_footer(self, ctx: Context):
        name = ""
        avatar = ""
        if self.__is_user_specific:
            if self.__specified_user is not None:
                name = self.__specified_user.display_name
                avatar = self.__specified_user.avatar_url_as(static_format="png", size=64)
            else:
                name = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png", size=64)
        if self.__footer_text is not None:
            if len(avatar) > 0:
                name = name + " | "
            name = name + self.__footer_text
        if len(name) > 0:
            self.__embed.set_footer(text=name, icon_url=avatar)

    async def __add_options(self, ctx: Context):
        if len(self.__embed.fields) > 0:
            string = await s.get_string(ctx, "amadeusMenu", "options")
            value = "***__" + string.string + "__***"
            self.__embed.add_field(name="\u200b", value=value, inline=False)

        for i, option in enumerate(self.__options):
            name = self.bot.config["bot"]["menu_emoji"][i] + " " + option.name
            if option.value is not None:
                value = option.value
            else:
                value = "\u200b"
            self.__reaction_emoji.append(self.bot.config["bot"]["menu_emoji"][i])
            self.__embed.add_field(name=name, value=value)

    async def __add_reactions(self, message: Message):
        for emoji in self.__reaction_emoji:
            await message.add_reaction(emoji=emoji)

    async def __await_user_reaction(self, ctx: Context, message: Message, timeout_seconds: int):
        def check(reaction, user):
            result = False
            if user != message.author and reaction.message.id == message.id:
                if self.__is_user_specific:
                    if self.__specified_user is not None:
                        if user == self.__specified_user:
                            result = True
                    elif user == ctx.author:
                        result = True
                else:
                    result = True
            return result

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=timeout_seconds, check=check)
            except asyncio.TimeoutError:
                if self.__clear_on_timeout:
                    await message.clear_reactions()
                self.__result.message = message
                self.__result.status = AmadeusMenuStatus.TIMEOUT
                return
            else:
                if reaction.emoji in self.__reaction_emoji:
                    await message.clear_reactions()
                    self.__result.status = AmadeusMenuStatus.SELECTED
                    self.__result.message = message
                    self.__result.reaction_index = self.__reaction_emoji.index(reaction.emoji)
                    self.__result.reaction_emoji = reaction.emoji
                    return
                else:
                    await message.remove_reaction(reaction.emoji, user)
