from enum import Enum

import discord
from discord.ext import commands
from components import checks, amadeusPrompt, amadeusMenu
from components.enums import ConfigStatus


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='config')
    @commands.check(checks.block_dms)
    async def config(self, ctx, *args):
        config_step = 0

        # gets set to false once a parameter the user submitted is invalid -> will ask for values from that point on
        input_still_valid = True

        # True if the first parameter submitted was an option instead of a category
        category_skipped = False

        # Length of args solely so we do not need to use len() over and over
        arg_length = len(args)

        message = None
        category = None
        option = None
        value = None

        while True:
            if config_step == 0:
                if arg_length > 0:
                    category = await self.get_category(ctx, args[0])
                    if category is not None:
                        config_step = 1
                    else:
                        # if value submitted by user is not a category, check if it's an option in any category
                        option_data = await self.get_option(ctx, args[0])
                        if option_data is None:
                            # if value submitted by user is not an option either, ask user for a category
                            input_still_valid = False
                            category_data = await self.ask_for_category(ctx)
                            if category_data is not None:
                                message = category_data[0]
                                category = category_data[1]
                                config_step = 1
                            else:
                                # stop config if user does not select a category
                                return
                        else:
                            # if value user submitted *was* an option, skip to step 2 with cat and opt from get_option
                            category_skipped = True
                            category = option_data[0]
                            option = option_data[1]
                            config_step = 2
                else:
                    # if user did not submit any parameters, ask for category
                    input_still_valid = False
                    category_data = await self.ask_for_category(ctx)
                    if category_data is not None:
                        message = category_data[0]
                        category = category_data[1]
                        config_step = 1
                    else:
                        # stop config if user does not select a category
                        return

            if config_step == 1:
                # If there's another argument and previous input was valid, check if option
                if arg_length > 1 and input_still_valid:
                    if category_skipped:
                        option_data = await self.get_option(ctx, args[0], category)
                    else:
                        option_data = await self.get_option(ctx, args[1], category)
                    # If input was indeed an option
                    if option_data is not None:
                        category = option_data[0]
                        option = option_data[1]
                        config_step = 2
                    else:
                        input_still_valid = False
                        option_data = await self.ask_for_option(ctx, category, message)
                        if option_data is not None:
                            message = option_data[0]
                            option = option_data[1]
                            config_step = 2
                        else:
                            # stop config if user does not select an option
                            return
                else:
                    input_still_valid = False
                    option_data = await self.ask_for_option(ctx, category, message)
                    if option_data is not None:
                        message = option_data[0]
                        option = option_data[1]
                        config_step = 2
                    else:
                        # stop config if user does not select an option
                        return

            if config_step == 2:
                if input_still_valid:
                    if not category_skipped:
                        # check all remaining arguments in args (whether option is actually a list does not matter here)
                        if arg_length > 2:
                            await self.__check_value_data(ctx, category, option, [message, args[2:]])
                        else:
                            # set to False in case this will be needed when making changes down the road
                            input_still_valid = False
                            value_data = await self.show_info_and_ask_for_value(ctx, category, option, message)
                            message = value_data[0]
                            if value_data[1] is not None:
                                await self.__check_value_data(ctx, category, option, value_data)
                            else:
                                await self.__show_config_status(ctx, message, ConfigStatus.OTHER)
                    else:
                        # check all remaining arguments in args (whether option is actually a list does not matter here)
                        if arg_length > 1:
                            await self.__check_value_data(ctx, category, option, [message, args[1:]])
                        else:
                            # set to False in case this will be needed when making changes down the road
                            input_still_valid = False
                            value_data = await self.show_info_and_ask_for_value(ctx, category, option, message)
                            message = value_data[0]
                            if value_data[1] is not None:
                                await self.__check_value_data(ctx, category, option, value_data)
                            else:
                                await self.__show_config_status(ctx, message, ConfigStatus.OTHER)
                else:
                    value_data = await self.show_info_and_ask_for_value(ctx, category, option, message)
                    message = value_data[0]
                    if value_data[1] is not None:
                        await self.__check_value_data(ctx, category, option, value_data)
                    else:
                        await self.__show_config_status(ctx, message, ConfigStatus.OTHER)
                return

    async def ask_for_category(self, ctx):
        title = await self.bot.strings.get_string(ctx, "config", "select_category")
        menu = amadeusMenu.AmadeusMenu(self.bot, title)
        await menu.set_user_specific(True)
        category_names = []
        for category_key, category_val in self.bot.values.options.items():
            category_names.append(category_key)
            strings = await self.bot.strings.extract_config_strings(ctx, category_val)
            await menu.add_option(strings[0], strings[1])
        menu_data = await menu.show_menu(ctx, 120)
        if menu_data is not None:
            return [menu_data[0], category_names[menu_data[1]]]
        return None

    async def get_category(self, ctx, user_input):
        user_input = user_input.lower()
        if self.bot.values.options.get(user_input) is not None:
            return user_input
        else:
            for category_key, category_val in self.bot.values.options.items():
                if await self.check_value(ctx, category_val, user_input) is True:
                    return category_key
        return None

    async def get_option(self, ctx, user_input, category=None):
        user_input = user_input.lower()
        if category is not None and self.bot.values.options.get(category, {}).get("list", {}).get(user_input) is not None:
            return category, user_input

        for category_key, category_val in self.bot.values.options.items():
            for option_key, option_val in category_val.get("list").items():
                if await self.check_value(ctx, option_val, user_input) is True:
                    return category_key, option_key
        return None

    async def check_value(self, ctx, value, user_input):
        # check for value name in server language
        lang = await self.bot.strings.get_language(ctx)
        option = value.get("name", {}).get(lang)
        if option is not None and user_input == option.lower():
            return True
        elif lang != self.bot.strings.default_language:
            # if value does not have a name in specified language, check against default language
            option = value.get("name", {}).get(self.bot.strings.default_language)
            if option is not None and user_input == option.lower():
                return True
        return None

    async def ask_for_option(self, ctx, category, message):
        # prepare menu
        category = self.bot.values.options.get(category)
        category_values = await self.bot.strings.extract_config_strings(ctx, category)
        title = category_values[0]
        menu = amadeusMenu.AmadeusMenu(self.bot, title)
        await menu.set_description(category_values[1])
        await menu.set_user_specific(True)

        # add options to menu
        option_names = []
        for option_key, option_val in category["list"].items():
            option_names.append(option_key)
            strings = await self.bot.strings.extract_config_strings(ctx, option_val)
            await menu.add_option(strings[0], strings[1])

        menu_data = await menu.show_menu(ctx, 120, message)
        if menu_data is not None:
            return [menu_data[0], option_names[menu_data[1]]]
        return None

    async def show_info_and_ask_for_value(self, ctx, category, option, message):

        # prepare prompt
        option_full = self.bot.values.options.get(category).get("list").get(option)
        option_values = await self.bot.strings.extract_config_strings(ctx, option_full)
        title = option_values[0]
        prompt = amadeusPrompt.AmadeusPrompt(self.bot, title)
        await prompt.set_description(option_values[1])
        await prompt.set_user_specific(True)

        # add fields to prompt

        current_value = await self.__convert_current_value(ctx, category, option)

        field_title = await self.bot.strings.get_string(ctx, "config", "current_value")
        await prompt.add_field(field_title, current_value)

        field_title = await self.bot.strings.get_string(ctx, "config", "default_value")
        default_value = option_full.get("default")
        if default_value is not None:
            await prompt.add_field(field_title, default_value)

        # TODO add field about is_list

        prompt = await self.__add_valid_field(ctx, prompt, category, option)

        field_title = await self.bot.strings.get_string(ctx, "config", "internal_name")
        await prompt.add_field(field_title, option)

        return await prompt.show_prompt(ctx, 120, message)

    async def __convert_current_value(self, ctx, category, option):
        current_value = await self.bot.values.get_config(ctx, category, option)

        converted_input = await self.bot.values.prepare_input(category, option, str(current_value), ctx)

        if converted_input is not None or True:
            return converted_input
        return current_value

    async def __add_valid_field(self, ctx, prompt, category, option):
        field_value = await self.bot.values.get_valid_input(category, option)
        if field_value is None:
            return prompt

        field_title = await self.bot.strings.get_string(ctx, "config", "valid_entries")
        if field_value == "boolean":
            field_value = ["True", "False"]
            field_value = '\n'.join(field_value)
        elif field_value == "channel":
            field_value = await self.bot.strings.get_string(ctx, "config", "channel_type")
        elif field_value == "role":
            field_value = await self.bot.strings.get_string(ctx, "config", "role_type")
        else:
            field_value = '\n'.join(field_value)

        await prompt.add_field(field_title, field_value, False)
        return prompt

    async def __check_value_data(self, ctx, category, option, value_data):
        if value_data is None:
            return
        prepared_input = await self.bot.values.prepare_input(category, option, value_data[1], ctx)
        if isinstance(prepared_input, ConfigStatus):
            await self.__show_config_status(ctx, value_data[0], prepared_input)
            return
        status = await self.bot.values.set_config(ctx, category, option, prepared_input)
        await self.__show_config_status(ctx, value_data[0], status)

    async def __show_config_status(self, ctx, message, error):
        embed = discord.Embed()

        if error == ConfigStatus.OPTION_DOES_NOT_EXIST:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "OPTION_DOES_NOT_EXIST")
        elif error == ConfigStatus.CONVERSION_FAILED:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "CONVERSION_FAILED")
        elif error == ConfigStatus.NOT_IN_VALID_LIST:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "NOT_IN_VALID_LIST")
            embed.description = await self.bot.strings.get_string(ctx, "config_status", "NOT_IN_VALID_LIST_DESC")
        elif error == ConfigStatus.UNKNOWN_DATA_TYPE:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "UNKNOWN_DATA_TYPE")
        elif error == ConfigStatus.NOT_VALID_FOR_DATA_TYPE:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "NOT_VALID_FOR_DATA_TYPE")
            embed.description = await self.bot.strings.get_string(ctx, "config_status", "NOT_VALID_FOR_DATA_TYPE_DESC")
        elif error == ConfigStatus.TEXT_CHANNEL_NOT_FOUND:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "TEXT_CHANNEL_NOT_FOUND")
            embed.description = await self.bot.strings.get_string(ctx, "config_status", "TEXT_CHANNEL_NOT_FOUND_DESC")
        elif error == ConfigStatus.ROLE_NOT_FOUND:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "ROLE_NOT_FOUND")
            embed.description = await self.bot.strings.get_string(ctx, "config_status", "ROLE_NOT_FOUND_DESC")
        elif error == ConfigStatus.SAVE_SUCCESS:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "SAVE_SUCCESS")
        elif error == ConfigStatus.SAVE_FAIL:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "SAVE_FAIL")
        elif error == ConfigStatus.OTHER:
            embed.title = await self.bot.strings.get_string(ctx, "config_status", "OTHER")
        name = ctx.author.display_name
        avatar = ctx.author.avatar_url_as(static_format="png")
        embed.set_footer(text=name, icon_url=avatar)
        if message is not None:
            await message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Config(bot))
