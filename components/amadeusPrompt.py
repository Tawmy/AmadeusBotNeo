import asyncio
import discord


class AmadeusPrompt:
    def __init__(self, bot, title):
        self.bot = bot
        self.__is_user_specific = False
        self.__specified_user = None

        self.__embed = discord.Embed()
        self.__embed.title = title

    async def set_title(self, title):
        self.__embed.title = title

    async def set_description(self, description):
        self.__embed.description = description

    async def set_user_specific(self, is_user_specific, user=None):
        self.__is_user_specific = is_user_specific
        if user is not None:
            self.__specified_user = user

    async def show_prompt(self, ctx, timeout_seconds, message=None):
        if message is None:
            message = await ctx.send(embed=self.__embed)
        else:
            await message.edit(embed=self.__embed)
        user_input = await self.__await_user_input(ctx, timeout_seconds)
        return [user_input, message]

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
            await user_message.delete()
            return None
        else:
            await user_message.delete()
            return user_message.content
