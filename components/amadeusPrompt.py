import asyncio
import discord


class AmadeusPrompt:
    def __init__(self, bot, title):
        self.bot = bot
        self.__is_user_specific = False
        self.__specified_user = None
        self.__cancel_string = "cancel"

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

    async def set_cancel_string(self, cancel_string):
        self.__cancel_string = cancel_string

    async def show_prompt(self, ctx, timeout_seconds, message=None):
        await self.__prepare_footer(ctx)
        if message is None:
            message = await ctx.send(embed=self.__embed)
        else:
            await message.edit(embed=self.__embed)
        user_input = await self.__await_user_input(ctx, timeout_seconds)
        return [user_input, message]

    async def __prepare_footer(self, ctx):
        if self.__is_user_specific:
            if self.__specified_user is not None:
                name = self.__specified_user.display_name
                avatar = self.__specified_user.avatar_url_as(static_format="png")
            else:
                name = ctx.author.display_name
                avatar = ctx.author.avatar_url_as(static_format="png")
            name += " | Type \"" + self.__cancel_string + "\" to cancel"
            self.__embed.set_footer(text=name, icon_url=avatar)

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
            if user_message.content in [self.__cancel_string, "\"" + self.__cancel_string + "\""]:
                return None
            else:
                return user_message.content
