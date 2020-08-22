import discord
from discord import User


class AmadeusInput:
    """
    Parent class of Amadeus input classes.

    This input can be customised using:
    - set_user_specific: Sets if only one and optionally which user will be able to reply to the prompt
    - set_title: Change the title of the prompt
    - set_author: Set the embed author
    - set_description: Set the embed description
    - append_description: Append more text to the embed description
    - add_field: Add a field to the embed
    """
    def __init__(self):
        self.is_user_specific = False
        self.specified_user = None
        self.embed = discord.Embed()

    async def set_user_specific(self, is_user_specific: bool, user: User = None):
        """
        Sets if the input should be usable by one speficic user only.
        Defaults to context author if user is not speficied.

        Parameters
        -----------
        is_user_specific: bool
            Should input be user specific?
        user: User, optional
            Optional user the input should be usable by.
        """
        self.is_user_specific = is_user_specific
        if user is not None:
            self.specified_user = user

    async def set_title(self, title: str):
        self.embed.title = title

    async def set_author(self, name: str, url: str = "", icon_url: str = ""):
        """
        Sets the author of the amadeusInput.

        Parameters
        -----------
        name: str
            The name of the author.
        url: str, optional
            An optional url.
        icon_url: str, optional
            An optional icon url
        """
        self.embed.set_author(name=name, url=url, icon_url=icon_url)

    async def set_description(self, description: str):
        self.embed.description = description

    async def append_description(self, description: str):
        if self.embed.description is not None and len(self.embed.description) > 0:
            self.embed.description += description
        else:
            await self.set_description(description)

    async def add_field(self, name: str, description: str, inline: bool = True):
        if name is not None and description is not None:
            self.embed.add_field(name=name, value=description, inline=inline)