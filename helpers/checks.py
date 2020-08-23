import discord
from discord.ext.commands import Context
from helpers import general
import components.exceptions as ex


async def global_check(ctx: Context, bot, ) -> bool:
    if not bot.ready:
        raise ex.BotNotReady

    if ctx.command.name not in bot.config["bot"]["limits"]["no_global_check"] and ctx.guild is not None:
        guild_config = await general.deep_get_type(dict, bot.config, str(ctx.guild.id))

        # Is bot enabled on server? (set to True during setup)
        if ctx.command.name not in bot.config["bot"]["limits"]["no_enable_check"]:
            await check_bot_enabled(ctx, bot, guild_config)

        moderator_skip_enabled = await general.deep_get(bot.config, str(ctx.guild.id), "general", "mods_override_limits")

        if await check_moderator_skip(moderator_skip_enabled, await is_moderator(ctx, bot)) is False:
            await check_category_limits(ctx, guild_config)
            await check_command_limits(ctx, guild_config)

        # TODO time limits

    return True


async def is_moderator(ctx: Context, bot):
    return discord.utils.get(ctx.author.roles, id=bot.config[str(ctx.guild.id)]["essential_roles"]["mod_role"])


async def check_moderator_skip(skip_enabled: bool, is_moderator_bool: bool) -> bool:
    return True if skip_enabled and is_moderator else False


async def check_bot_enabled(ctx: Context, bot, guild_config: dict):
    bot_status = await general.deep_get(guild_config, "general", "enabled")
    if bot_status is None:
        if str(ctx.guild.id) in bot.corrupt_configs:
            raise ex.CorruptConfig
        else:
            raise ex.BotNotConfigured
    elif bot_status is False:
        raise ex.BotDisabled


async def check_category_limits(ctx: Context, guild_config: dict):
    guild_config_cat = await general.deep_get(guild_config, "limits", "categories")
    if guild_config_cat is None:
        return
    # Is extension enabled on server?
    if await general.deep_get(guild_config_cat, ctx.command.cog_name.lower(), "enabled") is False:
        raise ex.CategoryDisabled
    # Do not check for extension role limits if command has role limits specified
    elif not await command_has_role_limits(ctx, guild_config):
        # Does the extension have role limits?
        wl = await general.deep_get_type(list, guild_config_cat, ctx.command.cog_name.lower(), "roles", "whitelist")
        bl = await general.deep_get_type(list, guild_config_cat, ctx.command.cog_name.lower(), "roles", "blacklist")
        result = await check_role_limits(ctx, wl, bl)
        if result[0] == 1:
            raise ex.CategoryNoWhitelistedRole(result[1])
        elif result[0] == 2:
            raise ex.CategoryBlacklistedRole(result[1])


async def check_command_limits(ctx: Context, guild_config: dict):
    guild_config_com = await general.deep_get(guild_config, "limits", "commands")
    # Is command enabled on the server?
    if await general.deep_get(guild_config_com, ctx.command.name, "enabled") is False:
        raise ex.CommandDisabled

    # Does the command have channel limits?
    wl = await general.deep_get_type(list, guild_config_com, ctx.command.name, "channels", "whitelist")
    bl = await general.deep_get_type(list, guild_config_com, ctx.command.name, "channels", "blacklist")
    if len(wl) > 0 and ctx.channel.id not in wl:
        raise ex.CommandNotWhitelistedChannel
    if ctx.channel.id in bl:
        raise ex.CommandBlacklistedChannel

    # Does the command have role limits?
    wl = await general.deep_get_type(list, guild_config_com, ctx.command.name, "roles", "whitelist")
    bl = await general.deep_get_type(list, guild_config_com, ctx.command.name, "roles", "blacklist")
    result = await check_role_limits(ctx, wl, bl)
    if result[0] == 1:
        raise ex.CommandNoWhitelistedRole(result[1])
    if result[0] == 2:
        raise ex.CommandBlacklistedRole(result[1])


async def command_has_role_limits(ctx: Context, guild_config: dict) -> int:
    if guild_config is not None:
        wl = await general.deep_get_type(list, guild_config, ctx.command.name, "limits", "commands", "roles", "whitelist")
        bl = await general.deep_get_type(list, guild_config, ctx.command.name, "limits", "commands", "roles", "blacklist")
        return len(wl) + len(bl) > 0
    return False


async def check_role_limits(ctx, wl, bl):
    if len(wl) + len(bl) > 0:
        match = False
        for role in ctx.author.roles:
            # TODO check if this can throw exception if bl/wl is None
            if role.id in wl:
                match = True
            if role.id in bl:
                return [2, role]
        if len(wl) > 0 and match is False:
            role_list = []
            for role_id in wl:
                role_list.append(ctx.guild.get_role(role_id))
            return [1, role_list]
    return [0]
