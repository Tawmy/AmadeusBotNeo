from PIL import ImageDraw, ImageFont, Image
from discord.ext.commands import Context
from helpers import strings as s
from helpers.ffxiv_character import Character


async def add_character_name(ctx: Context, draw: ImageDraw.Draw, character: Character):

    if len(character.name.title) > 0:
        if character.name.position_top:
            cat = "title_top"
        else:
            cat = "title_bot"
        x_title, y_title = ctx.bot.ffxiv.get("NamePositions", {}).get(cat, {}).get("title").values()
        font = ImageFont.truetype('resources/ffxiv/Vollkorn-Regular.ttf', size=28)
        await __add_text_centered_at_point(draw, font, character.name.title, x_title, y_title)
    else:
        cat = "no_title"

    x_name, y_name = ctx.bot.ffxiv.get("NamePositions", {}).get(cat, {}).get("name").values()
    font = ImageFont.truetype('resources/ffxiv/Vollkorn-Regular.ttf', size=48)
    await __add_text_centered_at_point(draw, font, character.name.name, x_name, y_name)


async def add_job_levels(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=26)
    for ff_class in character.class_jobs:
        abbr = ff_class.get("Job", {}).get("Abbreviation")
        x, y = ctx.bot.ffxiv.get("JobPositions", {}).get(abbr).values()
        level = ff_class.get("Level")
        if level == 0:
            text = "-"
        else:
            text = str(level)
        txt_length_x, txt_length_y = draw.textsize(text, font=font)
        draw.text((x - txt_length_x / 2, y - txt_length_y / 2), text, fill='rgb(255, 255, 255)', font=font)


async def add_grand_company(ctx: Context, draw: ImageDraw.Draw, image: Image, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
    x_txt, y_txt = ctx.bot.ffxiv.get("Positions", {}).get("free_company").values()

    # add "new adventurer" string if no fc either, return
    if not character.grand_company.member_of:
        if not character.free_company.member_of:
            await __add_default_text(ctx, draw, font, x_txt, y_txt)
        return

    # add grand company name if user in no free company
    x_gc, y_gc = 0, 0
    if not character.free_company.member_of:
        x_gc, y_gc = await __add_grand_company_name(ctx, draw, font, x_txt, y_txt, character.grand_company.name)
    await __add_grand_company_icon(ctx, image, character.grand_company.name, character.free_company.member_of, x_gc, y_gc)


async def add_free_company(ctx: Context, draw: ImageDraw.Draw, character: Character):
    # TODO add FC logo
    if character.free_company.member_of:
        fc_text = character.free_company.name + " <" + character.free_company.tag + ">"
        font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
        x, y = ctx.bot.ffxiv.get("Positions", {}).get("free_company").values()
        txt_length_x, txt_length_y = draw.textsize(fc_text, font=font)
        draw.text((x - txt_length_x / 2, y), fc_text, fill='rgb(255, 255, 255)', font=font)


async def add_active_class_job(ctx: Context, image: Image, character: Character):
    job_icon = None
    if character.job.abbreviation is None:
        return
    elif character.job.is_base_class:
        job_icon = await __get_base_class_icon(ctx, character)
    if job_icon is None:
        job_icon = Image.open("resources/ffxiv/jobs/" + character.job.abbreviation + ".png")
    if job_icon is not None:
        x, y = ctx.bot.ffxiv.get("Positions", {}).get("active_job").values()
        image.paste(job_icon, (x, y), job_icon)


async def add_item_level(ctx: Context, draw: ImageDraw.Draw, character: Character):
    ilvl_total = 0
    ilvl_main_hand = 0
    has_offhand = False

    for slot, piece in character.gear.items():
        ilvl = piece.get("Item", {}).get("LevelItem")
        if slot == "OffHand":
            has_offhand = True
        elif slot == "MainHand":
            ilvl_main_hand = ilvl
        if slot != "SoulCrystal":
            ilvl_total = ilvl_total + ilvl

    if has_offhand is False:
        ilvl_total = ilvl_total + ilvl_main_hand

    # truncate, then convert to string
    ilvl_total = str(int(ilvl_total/13))

    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=34)
    x, y = ctx.bot.ffxiv.get("Positions", {}).get("item_level").values()
    draw.text((x, y), ilvl_total, fill='rgb(255, 255, 255)', font=font)


async def add_mount_percentage(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=34)
    x, y = ctx.bot.ffxiv.get("Positions", {}).get("mount_percentage").values()
    percentage_text = str(character.mounts.percentage) + "%"
    txt_length_x, txt_length_y = draw.textsize(percentage_text, font=font)
    x = x - txt_length_x
    draw.text((x, y), percentage_text, fill='rgb(255, 255, 255)', font=font)


async def add_minion_percentage(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=34)
    x, y = ctx.bot.ffxiv.get("Positions", {}).get("minion_percentage").values()
    percentage_text = str(character.minions.percentage) + "%"
    txt_length_x, txt_length_y = draw.textsize(percentage_text, font=font)
    x = x - txt_length_x
    draw.text((x, y), percentage_text, fill='rgb(255, 255, 255)', font=font)


async def add_server(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
    x, y = ctx.bot.ffxiv.get("Positions", {}).get("server").values()
    txt_length_x, txt_length_y = draw.textsize(character.server, font=font)
    x = x - txt_length_x
    draw.text((x, y), character.server, fill='rgb(255, 255, 255)', font=font)


async def add_attributes(ctx: Context, draw: ImageDraw.Draw, character: Character):
    job_attributes = ctx.bot.ffxiv.get("AttributePriorities", {}).get(character.job.abbr_job, {})
    attribute_positions = ctx.bot.ffxiv.get("AttributePositions", {})
    for i, attribute in enumerate(job_attributes):
        value = await __get_attribute_value(ctx, attribute, character.attributes)
        positions = attribute_positions.get(str(i), {})
        await __draw_attribute(draw, positions, attribute, value)


async def __add_text_centered_at_point(draw: ImageDraw.Draw, font: ImageFont, text: str, x: int, y: int):
    text_size_x, text_size_y = draw.textsize(text, font=font)
    draw.text((x - text_size_x / 2, y - text_size_y / 2), text, fill='rgb(0, 0, 0)', font=font)


async def __add_default_text(ctx: Context, draw: ImageDraw.Draw, font: ImageFont, x_txt: int, y_txt: int):
    string = await s.get_string(ctx, "ffxiv", "new_adventurer")
    txt_length_x, txt_length_y = draw.textsize(string.string, font=font)
    draw.text((x_txt - txt_length_x / 2, y_txt), string.string, fill='rgb(255, 255, 255)', font=font)


async def __add_grand_company_name(ctx: Context, draw: ImageDraw.Draw, font: ImageFont, x_txt: int, y_txt: int, gc: str) -> tuple:
    x_gc_offset, y_gc_offset = ctx.bot.ffxiv.get("Positions", {}).get("grand_company_offset").values()
    txt_length_x, txt_length_y = draw.textsize(gc, font=font)
    draw.text((x_txt - txt_length_x / 2 + x_gc_offset, y_txt), gc, fill='rgb(255, 255, 255)', font=font)

    x_gc = x_txt - txt_length_x / 2 - x_gc_offset
    y_gc = y_txt - txt_length_y / 2 + y_gc_offset
    return int(x_gc), int(y_gc)


async def __add_grand_company_icon(ctx: Context, image: ImageDraw, gc: str, in_fc: bool, x_gc: int, y_gc: int):
    filename = await __get_gc_filename(gc)
    if len(filename) > 0:
        gc_icon = Image.open("resources/ffxiv/" + filename + ".png")
        if in_fc:
            # position gc logo differently if user is in an fc as gc name not shown in that case
            x_gc, y_gc = ctx.bot.ffxiv.get("Positions", {}).get("grand_company").values()
        image.paste(gc_icon, (x_gc, y_gc), gc_icon)


async def __get_gc_filename(gc: str) -> str:
    if gc is not None:
        if gc == "Maelstrom":
            return "gc_m"
        elif gc == "Order of the Twin Adder":
            return "gc_o"
        elif gc == "Immortal Flames":
            return "gc_i"
    return ""


async def __get_base_class_icon(ctx: Context, character: Character) -> Image:
    job = ctx.bot.ffxiv.get("BaseClasses", {}).get(character.job.name)
    return Image.open("resources/ffxiv/jobs/" + job + ".png") if job is not None else None


async def __get_attribute_value(ctx: Context, attribute_name: str, char_attrs: list) -> str:
    attribute_dict = ctx.bot.ffxiv.get("AttributeIDs", {})
    attribute_index = attribute_dict.get(attribute_name)
    attribute_value = None
    for attr in char_attrs:
        if attr.get("Attribute").get("ID") == attribute_index:
            attribute_value = attr.get("Value")
    return str(attribute_value)


async def __draw_attribute(draw: ImageDraw.Draw, positions: dict, name: str, value: str):
    x_name, y_name = positions.get("name").values()
    x_value, y_value = positions.get("value").values()
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
    value_length_x, value_length_y = draw.textsize(value, font=font)
    x_value = x_value - value_length_x
    draw.text((x_name, y_name), name, fill='rgb(255, 255, 255)', font=font)
    draw.text((x_value, y_value), value, fill='rgb(255, 255, 255)', font=font)
