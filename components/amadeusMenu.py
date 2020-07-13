import asyncio
import discord

from dataclasses import dataclass
from components.enums import AmadeusMenuStatus
from components import strings as s


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
    def __init__(self, bot, prompt):
        self.bot = bot
        self.__is_user_specific = False
        self.__clear_on_timeout = True
        self.__specified_user = None
        self.__footer_text = None

        self.__embed = discord.Embed()
        self.__embed.title = prompt

        self.__options = []
        self.__reaction_emoji = []

        self.__result = AmadeusMenuResult()

    async def add_option(self, name: str, description=None):
        if name is not None:
            self.__options.append(Option(name, description))

    async def add_field(self, name: str, description: str, inline=True):
        if name is not None and description is not None:
            self.__embed.add_field(name=name, value=description, inline=inline)

    async def set_author(self, name, url="", icon_url=""):
        """Sets the author of the amadeusMenu.

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

    async def set_footer_text(self, text):
        self.__footer_text = text

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

    async def set_user_specific(self, is_user_specific, user=None):
        """Sets if the menu should be usable by one speficic user only.
        Defaults to context author if user is not speficied.

        Parameters
        -----------
        is_user_specific: :class:`bool`
            Should menu be user specific?.
        user: :class:`discord.User`
            Optional user the menu should be accessible by.
        """

        self.__is_user_specific = is_user_specific
        if user is not None:
            self.__specified_user = user

    async def set_clear_on_timeout(self, clear_on_timeout):
        """Sets if reactions should be removed on timeout.

        Parameters
        -----------
        clear_on_timeout: :class:`bool`
            Should reactions be cleared on timeout?
        """

        self.__clear_on_timeout = clear_on_timeout

    async def append_emoji(self, emoji_list):
        for emoji in emoji_list:
            self.__reaction_emoji.append(emoji)

    async def show_menu(self, ctx, timeout_seconds, message=None):
        """Displays the amadeusMenu and waits for user input. Edits message if specified.
        Returns AmadeusMenuResult object.

        Parameters
        -----------
        ctx: :class:`discord.ext.commands.Context`
            The invocation context.
        timeout_seconds: :class:`int`
            Timeout in seconds.
        message: :class:`discord.Message`
            Optional message. This will be edited if specified.
        """

        await self.__add_options(ctx)
        await self.__prepare_footer(ctx)
        if len(self.__options) == 0:
            return None
        else:
            if message is None:
                message = await ctx.send(embed=self.__embed)
            else:
                await message.edit(embed=self.__embed)
            self.__result.status = AmadeusMenuStatus.SHOWN
            await self.__add_reactions(message)
            await self.__await_user_reaction(ctx, message, timeout_seconds)
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

        if self.__result.status == AmadeusMenuStatus.SELECTED:
            string = await s.get_string(ctx, s.String("amadeusMenuStatus", "SELECTED"))
        elif self.__result.status == AmadeusMenuStatus.TIMEOUT:
            string = await s.get_string(ctx, s.String("amadeusMenuStatus", "TIMEOUT"))
        elif self.__result.status == AmadeusMenuStatus.CANCELLED:
            string = await s.get_string(ctx, s.String("amadeusMenuStatus", "CANCELLED"))
        elif self.__result.status == AmadeusMenuStatus.SHOWN:
            string = await s.get_string(ctx, s.String("amadeusMenuStatus", "SHOWN"))
        elif self.__result.status == AmadeusMenuStatus.NEW:
            string = await s.get_string(ctx, s.String("amadeusMenuStatus", "NEW"))
        if string is not None:
            self.__embed.title = string.string
        await self.__prepare_footer(ctx)
        self.__result.message = await self.__result.message.edit(embed=self.__embed)

    async def __prepare_footer(self, ctx):
        name = ""
        avatar = ""
        if self.__is_user_specific:
            if self.__specified_user is not None:
                name = self.__specified_user.display_name
                avatar = self.__specified_user.avatar_url_as(static_format="png")
            else:
                name = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png")
        if self.__footer_text is not None:
            if len(avatar) > 0:
                name = name + " | "
            name = name + self.__footer_text
        if len(name) > 0:
            self.__embed.set_footer(text=name, icon_url=avatar)

    async def __add_options(self, ctx):
        if len(self.__embed.fields) > 0:
            string = await s.get_string(ctx, s.String("amadeusMenu", "options"))
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

    async def __add_reactions(self, message):
        for emoji in self.__reaction_emoji:
            await message.add_reaction(emoji=emoji)

    async def __await_user_reaction(self, ctx, message, timeout_seconds):
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
