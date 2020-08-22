from collections import defaultdict
from typing import Union

import discord
from discord.ext import commands
from discord.ext.commands import Context

from components import checks
from components.amadeusMenu import AmadeusMenu, AmadeusMenuStatus, AmadeusMenuResult
from components.amadeusPrompt import AmadeusPrompt, AmadeusPromptStatus, AmadeusPromptResult
from helpers import strings as s, limits, general
from helpers.config import save_config
from helpers.limits import InputData, LimitStep, OuterScope, InnerScope, EditType, ConfigType, LimitStatus, \
    PreparedInput


class Config(commands.Cog):
    def __init__(self, bot, *args):
        self.bot = bot

    @commands.command(name='limits')
    @commands.check(checks.block_dms)
    async def limits(self, ctx, *args):
        input_data = InputData()
        if len(args) > 0:
            await self.check_input(args, input_data)
        await self.collect_limits_data(ctx, input_data)

    async def check_input(self, args, input_data: InputData) -> InputData:
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
                                if input_data.inner_scope == InnerScope.ENABLED:
                                    input_data.values = args[3]
                                    input_data.limit_step = LimitStep.VALUES
                                    return input_data
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
                                if input_data.inner_scope == InnerScope.ENABLED:
                                    input_data.limit_step = LimitStep.EDIT_TYPE
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
            return InnerScope.ENABLED

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
        string_desc = await s.get_string(ctx, "limits", "category_desc")
        await menu.add_option(string.string, string_desc.string)
        string = await s.get_string(ctx, "limits", "command")
        string_desc = await s.get_string(ctx, "limits", "command_desc")
        await menu.add_option(string.string, string_desc.string)

        menu_data = await self.__show_menu_and_check_result(ctx, menu, input_data)
        if menu_data.status == AmadeusMenuStatus.SELECTED:
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

        if await self.__check_prompt_result(ctx, prompt, prompt_data, input_data):
            name = await self.get_name(input_data.outer_scope, prompt_data.input)
            if name is not None:
                input_data.limit_step = LimitStep.NAME
                input_data.message = prompt_data.message
                input_data.name = name
            else:
                await self.show_limit_status(ctx, input_data, LimitStatus.NAME_NOT_FOUND)

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
        title = await self.__get_menu_title(ctx, input_data)
        menu = AmadeusMenu(self.bot, title)
        await menu.set_user_specific(True)
        string = await s.get_string(ctx, "limits", "enabled")
        string_desc = await s.get_string(ctx, "limits", "enabled_desc")
        await menu.add_option(string.string, string_desc.string)
        string = await s.get_string(ctx, "limits", "role_s")
        string_desc = await s.get_string(ctx, "limits", "role_desc")
        await menu.add_option(string.string, string_desc.string)
        if input_data.outer_scope != OuterScope.CATEGORY:
            string = await s.get_string(ctx, "limits", "channel_s")
            string_desc = await s.get_string(ctx, "limits", "channel_desc")
            await menu.add_option(string.string, string_desc.string)
        await self.__add_current_values(ctx, input_data, menu)

        menu_data = await self.__show_menu_and_check_result(ctx, menu, input_data)
        if menu_data.status == AmadeusMenuStatus.SELECTED:
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
        title = await self.__get_menu_title(ctx, input_data)
        menu = AmadeusMenu(self.bot, title)
        await menu.set_user_specific(True)

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

        await self.__add_current_values(ctx, input_data, menu)

        menu_data = await self.__show_menu_and_check_result(ctx, menu, input_data)
        if menu_data.status == AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.CONFIG_TYPE
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.config_type = ConfigType.WHITELIST
            elif menu_data.reaction_index == 1:
                input_data.config_type = ConfigType.BLACKLIST

    async def ask_for_edit_type(self, ctx, input_data):
        title = await self.__get_menu_title(ctx, input_data)

        menu = AmadeusMenu(self.bot, title)
        await menu.set_user_specific(True)

        await self.__add_current_values(ctx, input_data, menu)

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

        menu_data = await self.__show_menu_and_check_result(ctx, menu, input_data)
        if menu_data.status == AmadeusMenuStatus.SELECTED:
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
        title = await self.__get_menu_title(ctx, input_data)
        menu = AmadeusMenu(self.bot, title)
        await menu.set_user_specific(True)

        string = await s.get_string(ctx, "limits", "enable")
        await menu.add_option(string.string)
        string = await s.get_string(ctx, "limits", "disable")
        await menu.add_option(string.string)

        menu_data = await self.__show_menu_and_check_result(ctx, menu, input_data)
        if menu_data.status == AmadeusMenuStatus.SELECTED:
            input_data.message = menu_data.message
            if menu_data.reaction_index == 0:
                input_data.values = "true"
            elif menu_data.reaction_index == 1:
                input_data.values = "false"
            input_data.limit_step = LimitStep.VALUES

    async def ask_for_values(self, ctx: Context, input_data: InputData):
        title = await self.__get_menu_title(ctx, input_data)
        prompt = AmadeusPrompt(self.bot, title)
        desc_string = None
        if input_data.edit_type == EditType.ADD:
            desc_string = await s.get_string(ctx, "limits", "add_desc")
        elif input_data.edit_type == EditType.REMOVE:
            desc_string = await s.get_string(ctx, "limits", "remove_desc")
        elif input_data.edit_type == EditType.REPLACE:
            desc_string = await s.get_string(ctx, "limits", "replace_desc")
        elif input_data.edit_type == EditType.RESET:
            desc_string = await s.get_string(ctx, "limits", "reset_desc")
        if desc_string is not None:
            await prompt.set_description(desc_string.string)

        await self.__add_current_values(ctx, input_data, prompt)

        prompt_data = await prompt.show_prompt(ctx, 120, input_data.message)
        if await self.__check_prompt_result(ctx, prompt, prompt_data, input_data):
            input_data.message = prompt_data.message
            input_data.values = prompt_data.input
            input_data.limit_step = LimitStep.VALUES

    async def process_input(self, ctx: Context, input_data: InputData):
        prepared_input = await limits.prepare_input(ctx, input_data.inner_scope, input_data.values)
        if prepared_input.successful:
            input_data.prepared_values = prepared_input.list
            input_data.limit_step = LimitStep.PREPARED
        else:
            if input_data.inner_scope == InnerScope.ROLE:
                await self.show_limit_status(ctx, input_data, LimitStatus.ROLE_NOT_FOUND)
            elif input_data.inner_scope == InnerScope.CHANNEL:
                await self.show_limit_status(ctx, input_data, LimitStatus.TEXT_CHANNEL_NOT_FOUND)

    async def save_limits(self, ctx: Context, input_data: InputData):
        await limits.set_limit(ctx, input_data)
        if await save_config(ctx):
            await self.show_limit_status(ctx, input_data, LimitStatus.SAVE_SUCCESS)
        else:
            await self.show_limit_status(ctx, input_data, LimitStatus.SAVE_FAIL)

    async def __get_menu_title(self, ctx: Context, input_data: InputData):
        outer_scope_str = await s.get_string(ctx, "limits", input_data.outer_scope.name.lower())
        return input_data.name.capitalize() + " " + outer_scope_str.string

    async def __add_edit_type_to_title(self, ctx: Context, input_data: InputData) -> str:
        if input_data.edit_type is not None:
            edit_type = None
            if input_data.edit_type == EditType.ADD:
                edit_type = "add_to"
            elif input_data.edit_type == EditType.REMOVE:
                edit_type = "remove_from"
            elif input_data.edit_type == EditType.REPLACE:
                edit_type = "replace_list"
            elif input_data.edit_type == EditType.RESET:
                edit_type = "reset_list"
            if edit_type is not None:
                string = await s.get_string(ctx, "limits", edit_type)
                return string.string if string is not None else ""
        return ""

    async def __add_inner_scope_to_title(self, ctx: Context, input_data: InputData) -> str:
        inner_scope_str = None
        if input_data.inner_scope == InnerScope.ROLE:
            inner_scope_str = await s.get_string(ctx, "limits", "role")
        elif input_data.inner_scope == InnerScope.CHANNEL:
            inner_scope_str = await s.get_string(ctx, "limits", "channel")
        if inner_scope_str is not None:
            return inner_scope_str.string
        else:
            await self.show_limit_status(ctx, input_data, LimitStatus.OTHER)

    async def __add_config_type_to_title(self, ctx: Context, input_data: InputData) -> str:
        config_type_str = None
        if input_data.config_type == ConfigType.WHITELIST:
            config_type_str = await s.get_string(ctx, "limits", "whitelist")
        elif input_data.config_type == ConfigType.BLACKLIST:
            config_type_str = await s.get_string(ctx, "limits", "blacklist")
        if config_type_str is not None:
            return " " + config_type_str.string
        else:
            await self.show_limit_status(ctx, input_data, LimitStatus.OTHER)

    async def __add_outer_scope_to_title(self, ctx: Context, input_data: InputData) -> str:
        outer_scope_str = None
        if input_data.outer_scope == OuterScope.CATEGORY:
            outer_scope_str = await s.get_string(ctx, "limits", "category")
        elif input_data.outer_scope == OuterScope.COMMAND:
            outer_scope_str = await s.get_string(ctx, "limits", "command")
        if outer_scope_str is not None:
            return " " + outer_scope_str.string
        else:
            await self.show_limit_status(ctx, input_data, LimitStatus.OTHER)

    async def show_limit_status(self, ctx: Context, input_data: InputData, status: LimitStatus):
        input_data.limit_step = LimitStep.FINISHED
        embed = discord.Embed()
        string_desc = None
        if status == LimitStatus.NAME_NOT_FOUND:
            string = await s.get_string(ctx, "limits_status", "NAME_NOT_FOUND")
            if input_data.outer_scope == OuterScope.CATEGORY:
                string_desc = await s.get_string(ctx, "limits_status", "NAME_NOT_FOUND_DESC_CATEGORY")
            elif input_data.outer_scope == OuterScope.COMMAND:
                string_desc = await s.get_string(ctx, "limits_status", "NAME_NOT_FOUND_DESC_COMMAND")
        elif status == LimitStatus.TEXT_CHANNEL_NOT_FOUND:
            string = await s.get_string(ctx, "config_status", "TEXT_CHANNEL_NOT_FOUND")
            string_desc = await s.get_string(ctx, "config_status", "TEXT_CHANNEL_NOT_FOUND_DESC")
        elif status == LimitStatus.ROLE_NOT_FOUND:
            string = await s.get_string(ctx, "config_status", "ROLE_NOT_FOUND")
            string_desc = await s.get_string(ctx, "config_status", "ROLE_NOT_FOUND_DESC")
        elif status == LimitStatus.SAVE_SUCCESS:
            string = await s.get_string(ctx, "limits_status", "SAVE_SUCCESS")
        else:
            string = await s.get_string(ctx, "config_status", "OTHER")
        embed.title = string.string
        if string_desc is not None and string_desc.successful:
            embed.description = string_desc.string

        # TODO this needs to be more dynamic, like set_footer in amadeusMenu
        # it works for now because config is always user specific
        name = ctx.author.display_name
        avatar = ctx.author.avatar_url_as(static_format="png")
        embed.set_footer(text=name, icon_url=avatar)

        if input_data.message is not None:
            await input_data.message.edit(embed=embed)
        else:
            await ctx.send(embed=embed)

    async def __add_current_values(self, ctx: Context, input_data: InputData, menu: Union[AmadeusMenu, AmadeusPrompt]):
        if await self.__check_field_enabled(input_data):
            await self.__add_field_to_menu(ctx, input_data, menu, InnerScope.ENABLED)
        if await self.__check_field_channel_whitelist(input_data):
            await self.__add_field_to_menu(ctx, input_data, menu, InnerScope.CHANNEL, ConfigType.WHITELIST)
        if await self.__check_field_channel_blacklist(input_data):
            await self.__add_field_to_menu(ctx, input_data, menu, InnerScope.CHANNEL, ConfigType.BLACKLIST)
        if await self.__check_field_role_whitelist(input_data):
            await self.__add_field_to_menu(ctx, input_data, menu, InnerScope.ROLE, ConfigType.WHITELIST)
        if await self.__check_field_role_blacklist(input_data):
            await self.__add_field_to_menu(ctx, input_data, menu, InnerScope.ROLE, ConfigType.BLACKLIST)

    async def __check_field_enabled(self, input_data: InputData):
        return input_data.config_type is None and input_data.inner_scope is None\
            or input_data.inner_scope == InnerScope.ENABLED

    async def __check_field_channel_whitelist(self, input_data: InputData):
        return input_data.config_type is None and input_data.inner_scope is None\
            or input_data.config_type is None and input_data.inner_scope == InnerScope.CHANNEL\
            or input_data.inner_scope == InnerScope.CHANNEL and input_data.config_type == ConfigType.WHITELIST

    async def __check_field_channel_blacklist(self, input_data: InputData):
        return input_data.config_type is None and input_data.inner_scope is None\
            or input_data.config_type is None and input_data.inner_scope == InnerScope.CHANNEL\
            or input_data.inner_scope == InnerScope.CHANNEL and input_data.config_type == ConfigType.BLACKLIST

    async def __check_field_role_whitelist(self, input_data: InputData):
        return input_data.config_type is None and input_data.inner_scope is None\
            or input_data.config_type is None and input_data.inner_scope == InnerScope.ROLE\
            or input_data.inner_scope == InnerScope.ROLE and input_data.config_type == ConfigType.WHITELIST

    async def __check_field_role_blacklist(self, input_data: InputData):
        return input_data.config_type is None and input_data.inner_scope is None\
            or input_data.config_type is None and input_data.inner_scope == InnerScope.ROLE\
            or input_data.inner_scope == InnerScope.ROLE and input_data.config_type == ConfigType.BLACKLIST

    async def __add_field_to_menu(self, ctx: Context, input_data: InputData, menu: AmadeusMenu, inner_scope: InnerScope, config_type: ConfigType = None):
        inner_scope_str = await s.get_string(ctx, "limits", inner_scope.name.lower())
        if inner_scope == InnerScope.ENABLED:
            title = inner_scope_str.string.capitalize()
        else:
            if config_type is None:
                return
            config_type_str = await s.get_string(ctx, "limits", config_type.name.lower())
            title = inner_scope_str.string.capitalize() + " " + config_type_str.string.capitalize()
        limit_list = await self.__get_list(ctx, input_data, inner_scope, config_type)
        prepared_input = await limits.prepare_input(ctx, inner_scope, limit_list, True)
        limit_list_str = await self.__get_limit_string(prepared_input, inner_scope)
        await menu.add_field(title, limit_list_str)

    async def __get_limit_string(self, prepared_input: PreparedInput, inner_scope: InnerScope):
        if len(prepared_input.list) > 0:
            return '\n'.join([str(element) for element in prepared_input.list])
        elif inner_scope == InnerScope.ENABLED and len(prepared_input.list) == 0:
            return "True"
        else:
            return "-"

    async def __get_list(self, ctx: Context, input_data: InputData, inner_scope: InnerScope, config_type: ConfigType) -> list:
        outer_scope_str = await limits.get_outer_scope_str(input_data)
        inner_scope_str = await limits.get_inner_scope_str(inner_scope)
        config_type_str = await limits.get_config_type_str(config_type)
        if inner_scope == InnerScope.ENABLED:
            return await general.deep_get_type(list, ctx.bot.config, str(ctx.guild.id), "limits", outer_scope_str, input_data.name.lower(), inner_scope_str)
        else:
            return await general.deep_get_type(list, ctx.bot.config, str(ctx.guild.id), "limits", outer_scope_str, input_data.name.lower(), inner_scope_str, config_type_str)

    async def __show_menu_and_check_result(self, ctx: Context, menu: AmadeusMenu, input_data: InputData) -> AmadeusMenuResult:
        await menu.set_footer_text(await limits.get_footer_text(ctx, input_data))
        menu_data = await menu.show_menu(ctx, 120, input_data.message)
        if menu_data.status != AmadeusMenuStatus.SELECTED:
            input_data.limit_step = LimitStep.FINISHED
            await menu.show_result(ctx)
        return menu_data

    async def __check_prompt_result(self, ctx: Context, prompt: AmadeusPrompt, prompt_data: AmadeusPromptResult, input_data: InputData) -> bool:
        if prompt_data.status != AmadeusPromptStatus.INPUT_GIVEN:
            input_data.limit_step = LimitStep.FINISHED
            await prompt.show_result(ctx)
            return False
        return True

def setup(bot):
    bot.add_cog(Config(bot))
