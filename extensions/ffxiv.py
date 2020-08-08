from dataclasses import dataclass
from io import BytesIO

import pyxivapi
import requests
from PIL import Image, ImageDraw, ImageFont
from discord.ext import commands


class FFXIV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ffchar')
    async def ffchar(self, ctx, first_name: str, last_name: str, server: str):
        character_id = await self.__find_character(first_name, last_name, server)
        if character_id is None:
            return  # TODO show status

        # load character data based on ID from __find_character
        character = await self.__request_character_data(character_id)

        # load background image, download character image, merge them
        image = await self.__load_images(character)
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=24)

        # add character name, fc when applicable, title when applicable
        await self.__add_character_name(draw, character)

        # add job levels
        await self.__add_job_levels(draw, font, character)


        await self.__add_grand_company(draw, image, character)
        await self.__add_free_company(draw, character)
        await self.__add_active_class_job(image, character)
        await self.__add_item_level(draw, character)
        await self.__add_mount_and_minion_percentages(draw, character)


        # image.save('rocket_pillow_paste_pos.jpg', quality=95)

    async def __find_character(self, first_name: str, last_name: str, server: str):
        client = pyxivapi.XIVAPIClient(api_key=self.bot.config["bot"]["ffxiv"]["api_key"])
        character = await client.character_search(
            world=server,
            forename=first_name,
            surname=last_name,
        )
        await client.session.close()
        if len(character.get("Results")) > 0:
            return character.get("Results")[0].get("ID")
        return None

    async def __request_character_data(self, character_id: int):
        client = pyxivapi.XIVAPIClient(api_key=self.bot.config["bot"]["ffxiv"]["api_key"])
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

    async def __load_images(self, character: dict):
        template = Image.open("resources/ffxiv/ffchar.png")
        background = Image.new('RGB', template.size, color='grey')
        response = requests.get(character.get("Character", {}).get("Portrait"))
        character = Image.open(BytesIO(response.content))
        character = character.crop((40, 0, 600, 873))
        # portrait height is 873px, hence the 27 above
        background.paste(character, (0, background.height - character.height))
        background.paste(template, (0, 0), template)
        return background

    async def __add_character_name(self, draw: ImageDraw.Draw, character: dict):
        name = character.get("Character", {}).get("Name")
        title = character.get("Character", {}).get("Title", {}).get("Name")

        if len(title) > 0:
            title = "<" + title + ">"
            if character.get("Character", {}).get("TitleTop"):
                cat = "title_top"
            else:
                cat = "title_bot"
            x_title, y_title = self.bot.ffxiv.get("NamePositions", {}).get(cat, {}).get("title").values()
            font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=24)
            await self.__print_text_centered_at_point(draw, font, title, x_title, y_title)
        else:
            cat = "no_title"

        x_name, y_name = self.bot.ffxiv.get("NamePositions", {}).get(cat, {}).get("name").values()
        font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=38)
        await self.__print_text_centered_at_point(draw, font, name, x_name, y_name)

    async def __print_text_centered_at_point(self, draw, font, text, x, y):
        text_size_x, text_size_y = draw.textsize(text, font=font)
        draw.text((x - text_size_x / 2, y - text_size_y / 2), text, fill='rgb(0, 0, 0)', font=font)

    async def __add_job_levels(self, draw, font, character):
        for ff_class in character.get("Character", {}).get("ClassJobs"):
            abbr = ff_class.get("Job", {}).get("Abbreviation")
            x, y = self.bot.ffxiv.get("JobPositions", {}).get(abbr).values()
            level = ff_class.get("Level")
            if level == 0:
                text = "-"
            else:
                text = str(level)
            txt_length_x, txt_length_y = draw.textsize(text, font=font)
            draw.text((x - txt_length_x / 2, y - txt_length_y / 2), text, fill='rgb(255, 255, 255)', font=font)

    async def __add_grand_company(self, draw, image, character):
        if character.get("Character", {}).get("GrandCompany", {}).get("Company") is None:
            return
        gc = character.get("Character", {}).get("GrandCompany", {}).get("Company", {}).get("Name")
        filename = ""
        if gc == "Maelstrom":
            filename = "gc_m"
        elif gc == "Order of the Twin Adder":
            filename = "gc_o"
        elif gc == "Immortal Flames":
            filename = "gc_i"
        if len(filename) > 0:
            gc_icon = Image.open("resources/ffxiv/" + filename + ".png")
            x, y = self.bot.ffxiv.get("Positions", {}).get("grand_company").values()
            image.paste(gc_icon, (x, y), gc_icon)
        # add grand company name if user in no free company
        # TODO separate method, don't call _add_free_company if this applies
        if character.get("FreeCompany") is None:
            font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
            x, y = self.bot.ffxiv.get("Positions", {}).get("free_company").values()
            draw.text((x, y), gc, fill='rgb(255, 255, 255)', font=font)

    async def __add_free_company(self, draw, character):
        if character.get("FreeCompany") is not None:
            fc_name = character.get("FreeCompany", {}).get("Name")
            fc_tag = character.get("FreeCompany", {}).get("Tag")
            fc_text = fc_name + " <" + fc_tag + ">"
            font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=28)
            x, y = self.bot.ffxiv.get("Positions", {}).get("free_company").values()
            draw.text((x, y), fc_text, fill='rgb(255, 255, 255)', font=font)

    async def __add_active_class_job(self, image, character):
        job = character.get("Character", {}).get("ActiveClassJob", {}).get("Job", {}).get("Abbreviation")
        if job is None:
            return
        job_icon = Image.open("resources/ffxiv/jobs/" + job + ".png")
        x, y = self.bot.ffxiv.get("Positions", {}).get("active_job").values()
        image.paste(job_icon, (x, y), job_icon)

    async def __add_item_level(self, draw, character):
        ilvl_total = 0
        ilvl_main_hand = 0
        has_offhand = False

        for slot, piece in character.get("Character").get("GearSet", {}).get("Gear").items():
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
        x, y = self.bot.ffxiv.get("Positions", {}).get("item_level").values()
        draw.text((x, y), ilvl_total, fill='rgb(255, 255, 255)', font=font)

    async def __add_mount_and_minion_percentages(self, draw, character):
        values = {
            "Mounts": {
                "total": "Mount",
                "character": "Mounts",
                "json": "mount_percentage"
            },
            "Minions": {
                "total": "Companion",
                "character": "Minions",
                "json": "minion_percentage"
            }
        }
        for value in values.values():
            client = pyxivapi.XIVAPIClient(api_key=self.bot.config["bot"]["ffxiv"]["api_key"])
            url = f'https://xivapi.com/search?indexes={value.get("total")}&filters=Order%3E=0&limit=1'
            async with client.session.get(url) as response:
                response_json = await response.json()
                mounts_total = response_json.get("Pagination", {}).get("ResultsTotal")
            await client.session.close()
            mounts_character = len(character.get(value.get("character")))
            mounts_percentage = int(round(mounts_character / mounts_total * 100))
            mounts_percentage = str(mounts_percentage) + "%"
            font = ImageFont.truetype('resources/ffxiv/OpenSans-Regular.ttf', size=34)
            x, y = self.bot.ffxiv.get("Positions", {}).get(value.get("json")).values()
            draw.text((x, y), mounts_percentage, fill='rgb(255, 255, 255)', font=font)


def setup(bot):
    bot.add_cog(FFXIV(bot))
