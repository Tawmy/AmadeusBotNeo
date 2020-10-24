import datetime
from io import BytesIO

import pyxivapi
import requests
from PIL import Image, ImageDraw, ImageFont
from discord import File
from discord.ext.commands import Context
from helpers import strings as s

from extensions.ffxiv.dataclasses import Character, Collection, FreeCompany, GrandCompany, Job, Name


async def find_character(ctx: Context, first_name: str, last_name: str, server: str):
    client = pyxivapi.XIVAPIClient(api_key=ctx.bot.config["bot"]["ffxiv"]["api_key"])
    character = await client.character_search(
        world=server,
        forename=first_name,
        surname=last_name,
    )
    await client.session.close()
    if len(character.get("Results")) > 0:
        return character.get("Results")[0].get("ID")
    return None


async def request_character_data(ctx: Context, character_id: int):
    client = pyxivapi.XIVAPIClient(api_key=ctx.bot.config["bot"]["ffxiv"]["api_key"])
    character = await client.character_by_id(
        lodestone_id=character_id,
        extended=True,  # extended includes title string, not just id
        include_freecompany=True,
        include_classjobs=True,
        include_minions_mounts=True
    )
    # TODO check behaviour when character ID does not exist
    await client.session.close()
    if character is not None:
        return character
    return None


async def crop_character_portrait(background: Image, character: Character):
    portrait = character.portrait.crop((63, 0, 577, 873))
    portrait = portrait.resize((459, 780))
    background.paste(portrait, (18, 64))


async def load_character_frame(background: Image):
    frame = Image.open("resources/ffxiv/frame.png")
    background.paste(frame, (18, 22), frame)


async def send_character_sheet(ctx: Context, image: ImageDraw, character: Character):
    filename = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S") + "_"
    filename += character.name.name + ".jpg"
    with BytesIO() as image_binary:
        image.save(image_binary, 'JPEG', quality=90)
        image_binary.seek(0)
        await ctx.send(file=File(fp=image_binary, filename=filename))


async def get_character(ctx: Context, character_raw: dict) -> Character:
    name = await __get_name(character_raw)
    job = await __get_job(character_raw)
    server = character_raw.get("Character", {}).get("Server")
    portrait = await __get_portrait(character_raw)
    class_jobs = character_raw.get("Character", {}).get("ClassJobs")
    gear = character_raw.get("Character").get("GearSet", {}).get("Gear")
    attributes = character_raw.get("Character", {}).get("GearSet", {}).get("Attributes")
    minions = await __get_minions(ctx, character_raw)
    mounts = await __get_mounts(ctx, character_raw)
    gc = await __get_grand_company(character_raw)
    fc = await __get_free_company(character_raw)
    return Character(name, job, server, portrait, class_jobs, gear, attributes, minions, mounts, gc, fc)


async def __get_name(character_raw: dict) -> Name:
    name = character_raw.get("Character", {}).get("Name")
    title = character_raw.get("Character", {}).get("Title", {}).get("Name")
    position_top = character_raw.get("Character", {}).get("TitleTop")
    return Name(name, title, position_top)


async def __get_job(character_raw: dict) -> Job:
    current_name = character_raw.get("Character", {}).get("ActiveClassJob", {}).get("UnlockedState", {}).get("Name")
    class_name = character_raw.get("Character", {}).get("ActiveClassJob", {}).get("Class", {}).get("Name")
    job_name = character_raw.get("Character", {}).get("ActiveClassJob", {}).get("Job", {}).get("Name")
    abbr_job = character_raw.get("Character", {}).get("ActiveClassJob", {}).get("Job", {}).get("Abbreviation")
    if current_name.lower() != job_name.lower() and current_name.lower() == class_name.lower():
        is_base_class = True
        abbreviation = character_raw.get("Character", {}).get("ActiveClassJob", {}).get("Class", {}).get("Abbreviation")
    else:
        is_base_class = False
        abbreviation = character_raw.get("Character", {}).get("ActiveClassJob", {}).get("Job", {}).get("Abbreviation")
    return Job(current_name, abbreviation, abbr_job, is_base_class)


async def __get_portrait(character_raw: dict) -> Image:
    response = requests.get(character_raw.get("Character", {}).get("Portrait"))
    return Image.open(BytesIO(response.content))
    # TODO check if this can throw exception on timeout or something


async def __get_mounts(ctx: Context, character_raw: dict) -> Collection:
    return await __calc_and_create_collection(ctx, character_raw, "Mount", "Mounts")


async def __get_minions(ctx: Context, character_raw: dict) -> Collection:
    return await __calc_and_create_collection(ctx, character_raw, "Companion", "Minions")


async def __get_grand_company(character_raw: dict) -> GrandCompany:
    if character_raw.get("Character", {}).get("GrandCompany", {}).get("Company") is None:
        return GrandCompany()
    name = character_raw.get("Character", {}).get("GrandCompany", {}).get("Company", {}).get("Name")
    icon = await __load_grand_company_icon(name)
    return GrandCompany(True, name, icon)


async def __get_free_company(character_raw: dict) -> FreeCompany:
    if character_raw.get("FreeCompany") is None:
        return FreeCompany()
    name = character_raw.get("FreeCompany", {}).get("Name")
    tag = character_raw.get("FreeCompany", {}).get("Tag")
    crest = await __get_free_company_crest(character_raw)
    return FreeCompany(True, name, tag, crest)


async def __calc_and_create_collection(ctx: Context, character_raw: dict, value_api: str, value_char: str) -> Collection:
    count_total = await __request_totals(ctx, value_api)
    count_character = len(character_raw.get(value_char))
    count_percentage = int(round(count_character / count_total * 100))
    return Collection(count_total, count_character, count_percentage)


async def __request_totals(ctx: Context, value: str):
    # value = "Mount" / "Companion"
    client = pyxivapi.XIVAPIClient(api_key=ctx.bot.config["bot"]["ffxiv"]["api_key"])
    url = f'https://xivapi.com/search?indexes={value}&filters=Order%3E=0&limit=1'
    async with client.session.get(url) as response:
        response_json = await response.json()
        count_total = response_json.get("Pagination", {}).get("ResultsTotal")
    await client.session.close()
    return count_total


async def __load_grand_company_icon(name: str) -> Image:
    filename = await __get_grand_company_filename(name)
    if len(filename) > 0:
        return Image.open("resources/ffxiv/" + filename + ".png")
    return None


async def __get_grand_company_filename(name: str) -> str:
    if name is not None:
        if name == "Maelstrom":
            return "gc_m"
        elif name == "Order of the Twin Adder":
            return "gc_o"
        elif name == "Immortal Flames":
            return "gc_i"
    return ""


async def __get_free_company_crest(character_raw: dict) -> Image:
    crest = character_raw.get("FreeCompany", {}).get("Crest")
    response = requests.get(crest[0])
    image1 = Image.open(BytesIO(response.content))
    response = requests.get(crest[1])
    image2 = Image.open(BytesIO(response.content))
    response = requests.get(crest[2])
    image3 = Image.open(BytesIO(response.content))
    image1.paste(image2, (0, 0), image2)
    image1.paste(image3, (0, 0), image3)
    image1 = image1.resize((52, 52))
    return image1


async def add_text_to_image(ctx: Context, draw: ImageDraw, image: Image, character: Character):
    await add_character_name(ctx, draw, character)
    await add_job_levels(ctx, draw, character)
    await add_grand_company(ctx, draw, image, character)
    await add_free_company(ctx, draw, image, character)
    await add_active_class_job(ctx, image, character)
    await add_item_level(ctx, draw, character)
    await add_mount_percentage(ctx, draw, character)
    await add_minion_percentage(ctx, draw, character)
    await add_server(ctx, draw, character)
    await add_attributes(ctx, draw, character)


async def add_character_name(ctx: Context, draw: ImageDraw.Draw, character: Character):

    if len(character.name.title) > 0:
        if character.name.position_top:
            cat = "title_top"
        else:
            cat = "title_bot"
        x_title, y_title = ctx.bot.values["ffxiv"].get("NamePositions", {}).get(cat, {}).get("title").values()
        font = ImageFont.truetype('resources/ffxiv/Vollkorn-Regular.ttf', size=28)
        await __add_text_centered_at_point(draw, font, character.name.title, x_title, y_title)
    else:
        cat = "no_title"

    x_name, y_name = ctx.bot.values["ffxiv"].get("NamePositions", {}).get(cat, {}).get("name").values()
    font = ImageFont.truetype('resources/ffxiv/Vollkorn-Regular.ttf', size=48)
    await __add_text_centered_at_point(draw, font, character.name.name, x_name, y_name)


async def add_job_levels(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=26)
    for ff_class in character.class_jobs:
        abbr = ff_class.get("Job", {}).get("Abbreviation")
        x, y = ctx.bot.values["ffxiv"].get("JobPositions", {}).get(abbr).values()
        level = ff_class.get("Level")
        if level == 0:
            text = "-"
        else:
            text = str(level)
        txt_length_x, txt_length_y = draw.textsize(text, font=font)
        draw.text((x - txt_length_x / 2, y - txt_length_y / 2), text, fill='rgb(255, 255, 255)', font=font)


async def add_grand_company(ctx: Context, draw: ImageDraw.Draw, image: Image, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
    x_txt, y_txt = ctx.bot.values["ffxiv"].get("Positions", {}).get("free_company").values()

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


async def add_free_company(ctx: Context, draw: ImageDraw.Draw, image: Image, character: Character):
    if character.free_company.member_of:
        fc_text = character.free_company.name + " <" + character.free_company.tag + ">"
        font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
        x, y = ctx.bot.values["ffxiv"].get("Positions", {}).get("free_company").values()
        x_fc_offset, y_fc_offset = ctx.bot.values["ffxiv"].get("Positions", {}).get("free_company_offset").values()
        txt_length_x, txt_length_y = draw.textsize(fc_text, font=font)
        draw.text((x - txt_length_x / 2 + x_fc_offset, y), fc_text, fill='rgb(255, 255, 255)', font=font)
        x_crest = int(x - txt_length_x / 2 - x_fc_offset)
        y_crest = int(y - y_fc_offset)
        image.paste(character.free_company.crest, (x_crest, y_crest))


async def add_active_class_job(ctx: Context, image: Image, character: Character):
    if character.job.abbreviation is None:
        return
    job_icon = Image.open("resources/ffxiv/jobs/" + character.job.abbreviation + ".png")
    if job_icon is not None:
        x, y = ctx.bot.values["ffxiv"].get("Positions", {}).get("active_job").values()
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
    x, y = ctx.bot.values["ffxiv"].get("Positions", {}).get("item_level").values()
    draw.text((x, y), ilvl_total, fill='rgb(255, 255, 255)', font=font)


async def add_mount_percentage(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=34)
    x, y = ctx.bot.values["ffxiv"].get("Positions", {}).get("mount_percentage").values()
    percentage_text = str(character.mounts.percentage) + "%"
    txt_length_x, txt_length_y = draw.textsize(percentage_text, font=font)
    x = x - txt_length_x
    draw.text((x, y), percentage_text, fill='rgb(255, 255, 255)', font=font)


async def add_minion_percentage(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=34)
    x, y = ctx.bot.values["ffxiv"].get("Positions", {}).get("minion_percentage").values()
    percentage_text = str(character.minions.percentage) + "%"
    txt_length_x, txt_length_y = draw.textsize(percentage_text, font=font)
    x = x - txt_length_x
    draw.text((x, y), percentage_text, fill='rgb(255, 255, 255)', font=font)


async def add_server(ctx: Context, draw: ImageDraw.Draw, character: Character):
    font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
    x, y = ctx.bot.values["ffxiv"].get("Positions", {}).get("server").values()
    txt_length_x, txt_length_y = draw.textsize(character.server, font=font)
    x = x - txt_length_x
    draw.text((x, y), character.server, fill='rgb(255, 255, 255)', font=font)


async def add_attributes(ctx: Context, draw: ImageDraw.Draw, character: Character):
    job_attributes = ctx.bot.values["ffxiv"].get("AttributePriorities", {}).get(character.job.abbr_job, {})
    attribute_positions = ctx.bot.values["ffxiv"].get("AttributePositions", {})
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
    x_gc_offset, y_gc_offset = ctx.bot.values["ffxiv"].get("Positions", {}).get("grand_company_offset").values()
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
            x_gc, y_gc = ctx.bot.values["ffxiv"].get("Positions", {}).get("grand_company").values()
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


async def __get_attribute_value(ctx: Context, attribute_name: str, char_attrs: list) -> str:
    attribute_dict = ctx.bot.values["ffxiv"].get("AttributeIDs", {})
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