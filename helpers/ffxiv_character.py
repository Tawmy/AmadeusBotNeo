from dataclasses import dataclass
from io import BytesIO

import pyxivapi
import requests
from PIL import Image
from discord.ext.commands import Context


@dataclass
class Name:
    name: str
    title: str
    position_top: bool


@dataclass
class Job:
    name: str
    abbreviation: str
    abbr_job: str  # abbr_job is needed to fetch priority attributes from json file (these  depend on the job name)
    is_base_class: bool


@dataclass
class GrandCompany:
    member_of: bool = False
    name: str = None
    logo: Image = None


@dataclass
class FreeCompany:
    member_of: bool = False
    name: str = None
    tag: str = None
    crest: Image = None


@dataclass
class Collection:
    total: int
    collected: int
    percentage: int


@dataclass
class Character:
    name: Name
    job: Job
    server: str
    portrait: Image
    class_jobs: list
    gear: dict
    attributes: list
    minions: Collection
    mounts: Collection
    grand_company: GrandCompany
    free_company: FreeCompany


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
