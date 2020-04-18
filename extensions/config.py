from discord.ext import commands
from components import checks, amadeusPrompt, amadeusMenu


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
                    category = await self.get_category(args[0])
                    if category is not None:
                        config_step = 1
                    else:
                        # if value submitted by user is not a category, check if it's an option in any category
                        option_data = await self.get_option(args[0])
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
                        option_data = await self.get_option(args[0], category)
                    else:
                        option_data = await self.get_option(args[1], category)
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
                # TODO
                print("Message: " + str(message))
                print("Category: " + str(category))
                print("Option: " + str(option))
                print("Value: " + str(value))
                print("still valid: " + str(input_still_valid))
                await message.delete()
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

    async def get_category(self, user_input):
        user_input = user_input.lower()
        if self.bot.values.options.get(user_input) is not None:
            return user_input
        else:
            for key, category in self.bot.values.options.items():
                for category_name in category.get("name").values():
                    if user_input == category_name.lower():
                        return key
        return None

    async def get_option(self, user_input, category=None):
        user_input = user_input.lower()
        if category is not None and self.bot.values.options.get(category, {}).get("list", {}).get(user_input) is not None:
            return category, user_input

        for category_key, category_val in self.bot.values.options.items():
            for option_key, option_val in category_val.get("list").items():
                # if user has entered exact name of option
                if user_input == option_key:
                    return user_input
                else:
                    # check if user has entered the name of the option in any language
                    for option_name in option_val.get("name").values():
                        if user_input == option_name.lower():
                            return category_key, option_key
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


def setup(bot):
    bot.add_cog(Config(bot))
