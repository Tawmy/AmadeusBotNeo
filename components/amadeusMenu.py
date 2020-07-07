import asyncio
import discord

from dataclasses import dataclass
from components.enums import AmadeusMenuStatus


@dataclass
class AmadeusMenuResult:
    status: AmadeusMenuStatus = AmadeusMenuStatus.NEW
    message: discord.message = None
    reaction_index: int = None
    reaction_emoji: str = None


class AmadeusMenu:
    def __init__(self, bot, prompt):
        self.bot = bot
        self.__is_user_specific = False
        self.__clear_on_timeout = True
        self.__specified_user = None

        self.__embed = discord.Embed()
        self.__embed.title = prompt

        self.__reaction_emoji = []

        self.__result = AmadeusMenuResult()

    async def set_options(self, names, descriptions=None):
        """Sets the options of the amadeusMenu.

        Parameters
        -----------
        names: :class:`list`
            A list of strings with options.
        descriptions: :class:`list`
            An optional list of descriptions for the menu options. Must be same length as names.
        """

        self.__embed.clear_fields()
        self.__reaction_emoji = []
        for i, name in enumerate(names):
            name = self.bot.config["bot"]["menu_emoji"][i] + " " + name
            if descriptions is not None and descriptions[i] is not None:
                value = descriptions[i]
            else:
                value = "\u200b"
            self.__embed.add_field(name=name, value=value)
            self.__reaction_emoji.append(self.bot.config["bot"]["menu_emoji"][i])

    async def add_option(self, name, description=None):
        name = self.bot.config["bot"]["menu_emoji"][len(self.__embed.fields)] + " " + name
        if description is not None:
            value = description
        else:
            value = "\u200b"
        self.__reaction_emoji.append(self.bot.config["bot"]["menu_emoji"][len(self.__embed.fields)])
        self.__embed.add_field(name=name, value=value)

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

        await self.__prepare_footer(ctx)
        if len(self.__embed.fields) == 0 and len(self.__reaction_emoji) == 0:
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

    async def show_result(self, timeout_seconds=None):
        embed = discord.embed()


    async def __prepare_footer(self, ctx):
        if self.__is_user_specific:
            if self.__specified_user is not None:
                name = self.__specified_user.display_name
                avatar = self.__specified_user.avatar_url_as(static_format="png")
            else:
                name = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png")
            self.__embed.set_footer(text=name, icon_url=avatar)

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
