import asyncio
import discord


class AmadeusMenu:
    def __init__(self, bot, prompt):
        self.bot = bot
        self.__is_user_specific = False
        self.__specified_user = None

        self.__embed = discord.Embed()
        self.__embed.title = prompt

        self.__reaction_emoji = []

    async def set_options(self, names, descriptions=None):
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

    async def set_title(self, title):
        self.__embed.title = title

    async def set_description(self, description):
        self.__embed.description = description

    async def set_user_specific(self, is_user_specific, user=None):
        self.__is_user_specific = is_user_specific
        if user is not None:
            self.__specified_user = user

    async def append_emoji(self, emoji_list):
        for emoji in emoji_list:
            self.__reaction_emoji.append(emoji)

    async def show_menu(self, ctx, timeout_seconds, message=None):
        if len(self.__embed.fields) == 0 and len(self.__reaction_emoji) == 0:
            return None
        else:
            if message is None:
                message = await ctx.send(embed=self.__embed)
            else:
                await message.edit(embed=self.__embed)
            await self.__add_reactions(message)
            return await self.__await_user_reaction(ctx, message, timeout_seconds)

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
                return None
            else:
                if reaction.emoji in self.__reaction_emoji:
                    await message.clear_reactions()
                    return [self.__reaction_emoji.index(reaction.emoji), message]
                else:
                    await message.remove_reaction(reaction.emoji, user)
