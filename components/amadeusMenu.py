import asyncio
import discord


class AmadeusMenu:
    def __init__(self, bot, prompt):
        self.bot = bot
        self.__is_user_specific = False

        self.__embed = discord.Embed()
        self.__embed.title = prompt

        self.__reaction_emoji = None

    async def __set_option(self, name, emoji):
        self.__embed.add_field(name=name, value=emoji)
        self.__reaction_emoji.append(emoji)

    async def set_options(self, names):
        self.__embed.clear_fields()
        self.__reaction_emoji = []
        for i, name in enumerate(names):
            await self.__set_option(name, self.bot.config["bot"]["menu_emoji"][i])

    async def set_title(self, title):
        self.__embed.title = title

    async def set_description(self, description):
        self.__embed.description = description

    async def set_user_specific(self, is_user_specific):
        self.__is_user_specific = is_user_specific

    async def show_menu(self, ctx, timeout_seconds, message=None):
        if len(self.__embed.fields) > 0:
            if message is None:
                message = await ctx.send(embed=self.__embed)
            else:
                await message.edit(embed=self.__embed)
            await self.__add_reactions(message)
            return await self.__await_user_reaction(ctx, message, timeout_seconds)
        else:
            return None

    async def __add_reactions(self, message):
        for emoji in self.__reaction_emoji:
            await message.add_reaction(emoji=emoji)

    async def __await_user_reaction(self, ctx, message, timeout_seconds):
        def check(reaction, user):
            result = False
            if user != message.author and reaction.message.id == message.id:
                if self.__is_user_specific:
                    if user is ctx.author:
                        result = True
                else:
                    result = True
            return result

        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=timeout_seconds, check=check)
            except asyncio.TimeoutError:
                await message.delete()
                return None
            else:
                if reaction.emoji in self.__reaction_emoji:
                    await message.clear_reactions()
                    return [self.__reaction_emoji.index(reaction.emoji), message]
                else:
                    await message.remove_reaction(reaction.emoji, user)
