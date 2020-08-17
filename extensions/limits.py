from collections import defaultdict
from discord.ext import commands
from discord.ext.commands import Context

from components import checks
from components.amadeusMenu import AmadeusMenu, AmadeusMenuStatus
from components.amadeusPrompt import AmadeusPrompt, AmadeusPromptStatus
from helpers import strings as s, limits
from helpers.config import save_config
from helpers.limits import InputData, LimitStep, OuterScope, InnerScope, EditType, ConfigType


class Config(commands.Cog):
    def __init__(self, bot, *args):
        self.bot = bot

    @commands.command(name='limits')
    @commands.check(checks.block_dms)
    async def limits(self, ctx, *args):
        input_data = InputData()
        if len(args) > 0:
            await self.check_input(ctx, args, input_data)
        await self.collect_limits_data(ctx, input_data)

    async def check_input(self, ctx, args, input_data: InputData) -> InputData:
        outer_scope = await self.get_outer_scope(args[0])
        if outer_scope is not None:
            input_data.outer_scope = outer_scope
            if len(args) > 1:
                name = await self.get_name(input_data.outer_scope, args[1])
                if name is not None:
                    input_data.name = name
                    if len(args) > 2:
                        inner_scope = await self.get_inner_scope(args[2])
                        if inner_scope is not None:
                            input_data.inner_scope = inner_scope
                            if len(args) > 3:
                                config_type = await self.get_config_type(args[3])
                                if config_type is not None:
                                    input_data.config_type = config_type
                                    if len(args) > 4:
                                        edit_type = await self.get_edit_type(args[4])
                                        if edit_type is not None:
                                            input_data.edit_type = edit_type
                                            if len(args) > 5:
                                                input_data.values = args[5:]
                                                input_data.limit_step = LimitStep.VALUES
                                            else:
                                                input_data.limit_step = LimitStep.EDIT_TYPE
                                        else:
                                            input_data.limit_step = LimitStep.CONFIG_TYPE
                                    else:
                                        input_data.limit_step = LimitStep.CONFIG_TYPE
                                else:
                                    input_data.limit_step = LimitStep.INNER_SCOPE
                            else:
                                input_data.limit_step = LimitStep.INNER_SCOPE
                        else:
                            input_data.limit_step = LimitStep.NAME
                    else:
                        input_data.limit_step = LimitStep.NAME
                else:
                    input_data.limit_step = LimitStep.OUTER_SCOPE
            else:
                input_data.limit_step = LimitStep.OUTER_SCOPE
        else:
            input_data.limit_step = LimitStep.NO_INFO
        return input_data

    async def collect_limits_data(self, ctx, input_data: InputData):
        while input_data.limit_step is not LimitStep.FINISHED:
            if input_data.limit_step == LimitStep.NO_INFO:
                await self.ask_for_outer_scope(ctx, input_data)
            elif input_data.limit_step == LimitStep.OUTER_SCOPE:
                await self.ask_for_name(ctx, input_data)
            elif input_data.limit_step == LimitStep.NAME:
                await self.ask_for_inner_scope(ctx, input_data)
            elif input_data.limit_step == LimitStep.INNER_SCOPE:
                await self.ask_for_config_type(ctx, input_data)
            elif input_data.limit_step == LimitStep.CONFIG_TYPE:
                await self.ask_for_edit_type(ctx, input_data)
            elif input_data.limit_step == LimitStep.EDIT_TYPE and input_data.inner_scope != InnerScope.ENABLED:
                await self.ask_for_values(ctx, input_data)
            elif input_data.limit_step == LimitStep.EDIT_TYPE and input_data.inner_scope == InnerScope.ENABLED:
                await self.ask_for_enable(ctx, input_data)
            elif input_data.limit_step == LimitStep.VALUES:
                await self.process_input(ctx, input_data)
            elif input_data.limit_step == LimitStep.PREPARED:
                await self.save_limits(ctx, input_data)

    async def get_outer_scope(self, user_input: str):
        user_input = user_input.lower()
        if user_input in ["command", "cmd"]:
            return OuterScope.COMMAND
        elif user_input in ["category", "cat"]:
            return OuterScope.CATEGORY
        return None

    async def get_name(self, outer_scope: OuterScope, user_input: str) -> str:
        if outer_scope == OuterScope.CATEGORY:
            for cog in self.bot.cogs:
                if user_input.lower() == cog.lower():
                    return cog.lower()
        elif outer_scope == OuterScope.COMMAND:
            for command in self.bot.commands:
                if user_input.lower() == str(command).lower():
                    return str(command).lower()

    async def get_inner_scope(self, user_input) -> InnerScope:
        user_input = user_input.lower()
        if user_input in ["role", "roles"]:
            return InnerScope.ROLE
        elif user_input in ["channel", "channels"]:
            return InnerScope.CHANNEL
        elif user_input in ["enabled", "enable", "on"]:
            return ConfigType.ENABLED

    async def get_config_type(self, user_input) -> ConfigType:
        user_input = user_input.lower()
        if user_input in ["whitelist", "white list", "wl", "allow list", "allowlist", "al"]:
            return ConfigType.WHITELIST
        elif user_input in ["blacklist", "black list", "bl", "deny list", "denylist", "dl"]:
            return ConfigType.BLACKLIST

    async def get_edit_type(self, user_input) -> EditType:
        user_input = user_input.lower()
        if user_input in ["add", "append"]:
            return EditType.ADD
        elif user_input == "remove":
            return EditType.REMOVE
        elif user_input == "replace":
            return EditType.REPLACE
        elif user_input in ["reset", "default", "revert"]:
            return EditType.RESET

    async def ask_for_outer_scope(self, ctx, input_data: InputData):
        string = await s.get_string(ctx, "limits", "select_outer_scope")
        menu = AmadeusMenu(self.bot, string.string)
        await menu.set_user_specific(True)

        string = await s.get_string(ctx, "limits", "category")
        await menu.add_option(string.string)
        string = await s.get_string(ctx, "limits", "command")
        await menu.add_option(string.string)

        menu_data = await menu.show_menu(ctx, 120)

        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.limit_step = LimitStep.OUTER_SCOPE
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.outer_scope = OuterScope.CATEGORY
            elif menu_data.reaction_index == 1:
                input_data.outer_scope = OuterScope.COMMAND

    async def ask_for_name(self, ctx, input_data: InputData):
        if input_data.outer_scope == OuterScope.CATEGORY:
            req_title = "category"
            req_description = "input_category"
        else:
            req_title = "command"
            req_description = "input_command"
        string_title = await s.get_string(ctx, "limits", req_title)
        string_description = await s.get_string(ctx, "limits", req_description)

        prompt = AmadeusPrompt(self.bot, string_title.string)
        await prompt.set_description(string_description.string)
        await prompt.set_user_specific(True)
        await self.__add_name_prompt_details(ctx, input_data.outer_scope, prompt)

        prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)

        if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
            input_data.limit_step = LimitStep.FINISHED
            await prompt.show_result(ctx)
        else:
            name = await self.get_name(input_data.outer_scope, prompt_data.input)
            if name is not None:
                input_data.limit_step = LimitStep.NAME
                input_data.message = prompt_data.message
                input_data.name = name
            else:
                pass
                # TODO show limit status with appropriate error message

    async def __add_name_prompt_details(self, ctx, outer_scope: OuterScope, prompt: AmadeusPrompt):
        cog_list = []
        for cog in self.bot.cogs:
            cog_list.append(cog.lower())
        if outer_scope == OuterScope.CATEGORY:
            cog_list_str = "\n".join(cog_list)
            string = await s.get_string(ctx, "limits", "categories")
            await prompt.add_field(string.string, cog_list_str)
        if outer_scope == OuterScope.COMMAND:
            cog_with_commands_dict = defaultdict(list)
            for command in self.bot.commands:
                if command.cog_name is not None and command.name not in self.bot.config["bot"]["no_limits"]:
                    cog_with_commands_dict[command.cog_name.lower()].append(command.name.lower())
            for cog_name, commands_list in cog_with_commands_dict.items():
                commands_str = "\n".join(commands_list)
                await prompt.add_field(cog_name, commands_str)

    async def ask_for_inner_scope(self, ctx, input_data: InputData):
        # TODO work on strings for inner and outer scope title
        string = await s.get_string(ctx, "limits", "select_inner_scope")
        menu = AmadeusMenu(self.bot, string.string)
        await menu.set_user_specific(True)
        string = await s.get_string(ctx, "limits", "enabled")
        string_desc = await s.get_string(ctx, "limits", "enabled_desc")
        await menu.add_option(string.string, string_desc.string)
        string = await s.get_string(ctx, "limits", "role")
        await menu.add_option(string.string)
        if input_data.outer_scope != OuterScope.CATEGORY:
            string = await s.get_string(ctx, "limits", "channel")
            await menu.add_option(string.string)
        menu_data = await menu.show_menu(ctx, 120, input_data.message)

        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.inner_scope = InnerScope.ENABLED
                input_data.limit_step = LimitStep.EDIT_TYPE
            else:
                input_data.limit_step = LimitStep.INNER_SCOPE
            if menu_data.reaction_index == 1:
                input_data.inner_scope = InnerScope.ROLE
            elif menu_data.reaction_index == 2:
                input_data.inner_scope = InnerScope.CHANNEL

    async def ask_for_config_type(self, ctx, input_data: InputData):
        # TODO show current config for wl, bl, and enabled
        string = await s.get_string(ctx, "limits", "select_config_type")
        menu = AmadeusMenu(self.bot, string.string)

        string = await s.get_string(ctx, "limits", "whitelist")
        req_desc = ""
        if input_data.inner_scope == InnerScope.ROLE:
            req_desc = "whitelist_desc_role"
        elif input_data.inner_scope == InnerScope.CHANNEL:
            req_desc = "whitelist_desc_channel"
        # TODO if req_desc = "" causes exception
        string_desc = await s.get_string(ctx, "limits", req_desc)
        await menu.add_option(string.string, string_desc.string)

        string = await s.get_string(ctx, "limits", "blacklist")
        req_desc = ""
        if input_data.inner_scope == InnerScope.ROLE:
            req_desc = "blacklist_desc_role"
        elif input_data.inner_scope == InnerScope.CHANNEL:
            req_desc = "blacklist_desc_channel"
        # TODO if req_desc = "" causes exception
        string_desc = await s.get_string(ctx, "limits", req_desc)
        await menu.add_option(string.string, string_desc.string)

        menu_data = await menu.show_menu(ctx, 120, input_data.message)

        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.limit_step = LimitStep.CONFIG_TYPE
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.config_type = ConfigType.WHITELIST
            elif menu_data.reaction_index == 1:
                input_data.config_type = ConfigType.BLACKLIST

    async def ask_for_edit_type(self, ctx, input_data):
        string = None
        if input_data.config_type == ConfigType.WHITELIST:
            string = await s.get_string(ctx, "limits", "whitelist")
        elif input_data.config_type == ConfigType.BLACKLIST:
            string = await s.get_string(ctx, "limits", "blacklist")
        connecting_string = await s.get_string(ctx, "limits", "for")
        title_str = string.string + connecting_string.string + input_data.name

        menu = AmadeusMenu(self.bot, title_str)
        await menu.set_user_specific(True)

        # TODO add field with current values

        string = await s.get_string(ctx, "limits", "add")
        string_desc = await s.get_string(ctx, "limits", "add_desc")
        await menu.add_option(string.string, string_desc.string)
        string = await s.get_string(ctx, "limits", "remove")
        string_desc = await s.get_string(ctx, "limits", "remove_desc")
        await menu.add_option(string.string, string_desc.string)
        string = await s.get_string(ctx, "limits", "replace")
        string_desc = await s.get_string(ctx, "limits", "replace_desc")
        await menu.add_option(string.string, string_desc.string)
        string = await s.get_string(ctx, "limits", "reset")
        string_desc = await s.get_string(ctx, "limits", "reset_desc")
        await menu.add_option(string.string, string_desc.string)

        menu_data = await menu.show_menu(ctx, 120, input_data.message)

        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.limit_step = LimitStep.EDIT_TYPE
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.edit_type = EditType.ADD
            elif menu_data.reaction_index == 1:
                input_data.edit_type = EditType.REMOVE
            elif menu_data.reaction_index == 2:
                input_data.edit_type = EditType.REPLACE
            elif menu_data.reaction_index == 3:
                input_data.edit_type = EditType.RESET

    async def ask_for_enable(self, ctx: Context, input_data: InputData):
        string = await s.get_string(ctx, "limits", "enable")
        title_str = string.string + " " + input_data.name
        if input_data.outer_scope == OuterScope.CATEGORY:
            string = await s.get_string(ctx, "limits", "category")
        elif input_data.outer_scope == OuterScope.COMMAND:
            string = await s.get_string(ctx, "limits", "command")
        title_str += " " + string.string
        menu = AmadeusMenu(self.bot, title_str)
        await menu.set_user_specific(True)

        string = await s.get_string(ctx, "limits", "enable")
        await menu.add_option(string.string)
        string = await s.get_string(ctx, "limits", "disable")
        await menu.add_option(string.string)

        menu_data = await menu.show_menu(ctx, 120, input_data.message)

        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.FINISHED
            await menu.show_result(ctx)
        else:
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.values = "true"
            elif menu_data.reaction_index == 1:
                input_data.values = "false"
            input_data.limit_step = LimitStep.VALUES

    async def ask_for_values(self, ctx: Context, input_data: InputData):
        edit_type = None
        if input_data.edit_type == EditType.ADD:
            edit_type = "add"
        elif input_data.edit_type == EditType.REMOVE:
            edit_type = "remove"
        elif input_data.edit_type == EditType.REPLACE:
            edit_type = "replace"
        elif input_data.edit_type == EditType.RESET:
            edit_type = "reset"
        edit_type_string = await s.get_string(ctx, "limits", edit_type) if edit_type is not None else ""

        string = None
        if input_data.config_type == ConfigType.WHITELIST:
            string = await s.get_string(ctx, "limits", "whitelist")
        elif input_data.config_type == ConfigType.BLACKLIST:
            string = await s.get_string(ctx, "limits", "blacklist")
        connecting_string = await s.get_string(ctx, "limits", "for")
        title_str = edit_type_string.string + " " + string.string + connecting_string.string + input_data.name

        prompt = AmadeusPrompt(self.bot, title_str)
        desc_string = await s.get_string(ctx, "limits", edit_type_string.string + "_desc")
        await prompt.set_description(desc_string.string)

        # TODO add field with current values

        prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)

        if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
            input_data.limit_step = LimitStep.FINISHED
            await prompt.show_result(ctx)
        else:
            input_data.message = prompt_data.message
            input_data.values = prompt_data.input
            input_data.limit_step = LimitStep.VALUES

    async def process_input(self, ctx: Context, input_data: InputData):
        prepared_input = await limits.prepare_input(ctx, input_data.inner_scope, input_data.values)
        if prepared_input.successful:
            input_data.prepared_values = prepared_input.list
            input_data.limit_step = LimitStep.PREPARED
        else:
            input_data.limit_step = LimitStep.FINISHED
            # todo show appropriate error message

    async def save_limits(self, ctx: Context, input_data: InputData):
        await limits.set_limit(ctx, input_data)
        input_data.limit_step = LimitStep.FINISHED
        if await save_config(ctx):
            pass  # todo show success message
        else:
            pass  # todo show appropriate error


def setup(bot):
    bot.add_cog(Config(bot))
