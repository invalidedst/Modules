#  _____                          
# |_   _|____  ____ _ _ __   ___  
#   | |/ _ \ \/ / _` | '_ \ / _ \ 
#   | | (_) >  < (_| | | | | (_) |
#   |_|\___/_/\_\__,_|_| |_|\___/ 
#                              
# meta banner: https://i.ibb.co/N2RJmphR/image-9956.jpg
# meta developer: @mqvon
# scope: @mqvon

import asyncio
import aiohttp
from hikka import loader, utils
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from io import BytesIO

@loader.tds
class AnimeFinderMod(loader.Module):
    strings = {
        "name": "AnimeFinder",
        "cfg_api_key": "API-ключ для Trace.moe (необязательно)",
        "cfg_cut_borders": "Обрезать границы изображения при поиске (True/False)"
    }
# хули смотришь выйди
    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                None,
                lambda: self.strings["cfg_api_key"],
                validator=loader.validators.Union(loader.validators.String(), loader.validators.NoneType())
            ),
            loader.ConfigValue(
                "cut_borders",
                True,
                lambda: self.strings["cfg_cut_borders"],
                validator=loader.validators.Boolean()
            )
        )

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    async def findanimecmd(self, message):
        """Ищет аниме по скриншоту (реплай на изображение)"""
        reply = await message.get_reply_message()
        if not reply or not isinstance(reply.media, (MessageMediaPhoto, MessageMediaDocument)):
            await message.edit("<emoji document_id=5352703271536454445>❌</emoji> Ответь на фото или GIF!")
            return

        await message.edit("<emoji document_id=5217592344957691550>🤨</emoji> Ищу аниме...")

        try:
            media = reply.media
            file = await self.client.download_media(media, bytes, thumb=-1)
            if not file:
                await message.edit("<emoji document_id=5352703271536454445>❌</emoji> Не смог скачать картинку!")
                return
        except:
            await message.edit("<emoji document_id=5352703271536454445>❌</emoji> Ошибка при скачивании!")
            return

        url = "https://api.trace.moe/search"
        params = {"anilistInfo": "1", "cutBorders": "1" if self.config["cut_borders"] else "0"}
        if self.config["api_key"]:
            params["key"] = self.config["api_key"]

        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("image", BytesIO(file), filename="image.jpg", content_type="image/jpeg")
                async with session.post(url, params=params, data=data) as resp:
                    if resp.status != 200:
                        await message.edit("<emoji document_id=5352703271536454445>❌</emoji> Ошибка API!")
                        return
                    result = await resp.json()
        except:
            await message.edit("<emoji document_id=5352703271536454445>❌</emoji> Не получилось связаться с API!")
            return

        if result.get("error"):
            await message.edit(f"<emoji document_id=5352703271536454445>❌</emoji> Ошибка: {result['error']}")
            return

        if not result.get("result") or not result["result"]:
            await message.edit("Аниме не найдено, попробуй другую картинку!")
            return

        debug_response = ""
        for idx, res in enumerate(result["result"][:3]):
            anilist = res.get("anilist", {})
            title = anilist.get("title", {})
            title_native = title.get("native", "Неизвестно")
            title_romaji = title.get("romaji", "Неизвестно")
            title_english = title.get("english", "Неизвестно")
            episode = res.get("episode", "Не указан")
            similarity = round(res.get("similarity", 0) * 100, 2)
            from_time = int(res.get("from", 0))
            to_time = int(res.get("to", 0))
            from_time_str = f"{from_time // 60:02d}:{from_time % 60:02d}"
            to_time_str = f"{to_time // 60:02d}:{to_time % 60:02d}"
            debug_response += (
                f"Результат {idx + 1}:\n"
                f"<emoji document_id=5206593182820741575>💚</emoji> Оригинал: <b>{title_native}</b>\n"
                f"<emoji document_id=5206593182820741575>💚</emoji> Ромадзи: <b>{title_romaji}</b>\n"
                f"<emoji document_id=5467887736000093669>🇬🇧</emoji> Английское: <b>{title_english}</b>\n"
                f"<emoji document_id=5336814422276992289>🌟</emoji> Эпизод: {episode}\n"
                f"<emoji document_id=5325583469344989152>⏳</emoji> Таймкод: {from_time_str} - {to_time_str}\n"
                f"<emoji document_id=5206587406089731561>⁉️</emoji> Схожесть: {similarity}%\n\n"
            )

        top_result = result["result"][0]
        anilist = top_result.get("anilist", {})
        title = anilist.get("title", {})
        title_native = title.get("native", "Неизвестно")
        title_romaji = title.get("romaji", "Неизвестно")
        title_english = title.get("english", "Неизвестно")
        episode = top_result.get("episode", "Не указан")
        similarity = round(top_result.get("similarity", 0) * 100, 2)
        from_time = int(top_result.get("from", 0))
        to_time = int(top_result.get("to", 0))
        from_time_str = f"{from_time // 60:02d}:{from_time % 60:02d}"
        to_time_str = f"{to_time // 60:02d}:{to_time % 60:02d}"

        title_russian = None
        synonyms = anilist.get("synonyms", [])
        for synonym in synonyms:
            if any(c in synonym.lower() for c in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
                title_russian = synonym
                break

        if not title_russian:
            title_russian = await self.get_russian_title(title_romaji, title_english)

        response = (
            f"<emoji document_id=5206593182820741575>💚</emoji> Оригинал: <b>{title_native}</b>\n"
            f"<emoji document_id=5206593182820741575>💚</emoji> Ромадзи: <b>{title_romaji}</b>\n"
            f"<emoji document_id=5467887736000093669>🇬🇧</emoji> Английское: <b>{title_english}</b>\n"
        )
        response += f"<emoji document_id=5461155860094921420>🇷🇺</emoji> Русское: <b>{title_russian}</b>\n" if title_russian else "<emoji document_id=5461155860094921420>🇷🇺</emoji> Русское: Не найдено\n"
        response += (
            f"<emoji document_id=5336814422276992289>🌟</emoji> Эпизод: {episode}\n"
            f"<emoji document_id=5325583469344989152>⏳</emoji> Таймкод: {from_time_str} - {to_time_str}\n"
            f"<emoji document_id=5206587406089731561>⁉️</emoji> Схожесть: {similarity}%"
        )

        if similarity < 90:
            response = (
                f"<emoji document_id=5312383351217201533>⚠️</emoji> Схожесть низкая, может быть неточно:\n\n"
                f"{response}\n\n"
                f"<emoji document_id=5332289648460853008>🌟</emoji> Все результаты:\n{debug_response}"
            )

        await message.edit(response)

    async def get_russian_title(self, romaji, english):
        if not romaji and not english:
            return None

        search_query = romaji if romaji != "Неизвестно" else english
        if search_query == "Неизвестно":
            search_query = english if english != "Неизвестно" else None
        if not search_query:
            return None

        search_query = search_query.replace("!", "").replace("*", "").strip()

        url = "https://shikimori.one/api/animes"
        params = {"search": search_query, "limit": 1}

        try:
            await asyncio.sleep(0.2)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        return None
                    results = await resp.json()
        except:
            return None

        if not results or not results:
            if search_query != english and english != "Неизвестно":
                return await self.get_russian_title(english, romaji)
            return None

        anime = results[0]
        title_russian = anime.get("russian") or anime.get("name")
        if title_russian and title_russian != romaji and title_russian != english:
            return title_russian
        return None
# хуй
    async def togglecutcmd(self, message):
        """Включает/выключает обрезку границ"""
        self.config["cut_borders"] = not self.config["cut_borders"]
        self.db.set(self.strings["name"], "cut_borders", self.config["cut_borders"])
        await message.edit(f"Обрезка границ {'включена' if self.config['cut_borders'] else 'выключена'} ✅")