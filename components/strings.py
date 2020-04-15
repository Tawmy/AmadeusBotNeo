import json


class Strings:
    def __init__(self):
        self.strings = []
        self.exception_strings = []

    async def load_strings(self):
        try:
            with open("values/strings.json", 'r') as json_file:
                try:
                    self.strings = json.load(json_file)
                except ValueError:
                    return False
            with open("values/exceptions.json", 'r') as json_file:
                try:
                    self.exception_strings = json.load(json_file)
                except ValueError:
                    return False
        except FileNotFoundError:
            return False
        return True

    async def get_string(self, ctx, category, name):
        lang = await self.__get_language(ctx)
        return self.strings.get(category, {}).get(name, {}).get(lang)

    async def get_config_strings(self, ctx, category, command_title):
        lang = await self.__get_language(ctx)
        config_option = ctx.bot.options.get(category, {}).get(command_title)
        if config_option is not None:
            name = config_option.get("name", {}).get(lang)
            description = config_option.get("description", {}).get(lang)
            return [name, description]
        return None

    async def get_exception_strings(self, ctx, exception_name):
        lang = await self.__get_language(ctx)
        exception = self.exception_strings.get(exception_name)
        if exception is not None:
            message = exception.get("message", {}).get(lang)
            description = exception.get("description", {}).get(lang)
            return [message, description]
        return None

    async def extract_config_strings(self, ctx, object):
        lang = await self.__get_language(ctx)
        name = object["name"][lang]
        description = object["description"][lang]
        if name is not None and description is not None:
            return [name, description]
        return None

    async def __get_language(self, ctx):
        if ctx.guild is not None:
            lang = ctx.bot.config.get(str(ctx.guild.id), {}).get("general", {}).get("language")
        else:
            lang = None
        if lang is not None:
            return lang
        else:
            return "en"

    async def insert_into_string(self, strings, values, position=None):
        if type(strings) is str:
            strings = [strings]
        if type(values) is str:
            values = [values]
        if len(strings) == len(values) + 1:
            string_with_values = strings[0]
            for i, value in enumerate(values):
                string_with_values += " "
                string_with_values += value
                string_with_values += " "
                string_with_values += strings[i + 1]
            return string_with_values
        elif len(strings) == len(values):
            string_with_values = ""
            if position == "left":
                for i, value in enumerate(values):
                    string_with_values += value
                    string_with_values += " "
                    string_with_values += strings[i]
                    string_with_values += " "
                return string_with_values
            elif position == "right":
                for i, string in enumerate(strings):
                    string_with_values += string
                    string_with_values += " "
                    string_with_values += values[i]
                    string_with_values += " "
                return string_with_values
        return None

    async def append_roles(self, string, roles):
        roles_string = string + "\n\n**"
        if type(roles) is list:
            roles_string += '**, **'.join(roles)
        else:
            roles_string += roles
        roles_string += "**"
        return roles_string
