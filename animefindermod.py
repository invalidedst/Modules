#  _                          
# |_   _|__   _ _    ___  
#   | |/ _ \ \/ / _` | '_ \ / _ \ 
#   | | (_) >  < (_| | | | | (_) |
#   |_|\_/_/\_\,_|_| |_|\___/ 
#                              
# meta banner: https://i.ibb.co/S7f3RT0Y/image-10097.jpg
# meta developer: @Toxano_Modules
# scope: @mqvon @Toxano_Modules

import asyncio
import aiohttp
import hashlib
import re
from typing import Optional, Dict
from io import BytesIO
from .. import loader, utils
from hikkatl.types import Message


@loader.tds
class AnimeFinderMod(loader.Module):
    """говно поиск аниме по скрину (новые аниме не ищит) """
    
    strings = {
        "name": "AnimeFinder",
        "searching": "🔍 <b>Searching for anime...</b>",
        "error_no_reply": "❌ <b>Reply to a photo, GIF or sticker!</b>",
        "error_download": "❌ <b>Failed to download image!</b>",
        "error_api": "❌ <b>Trace.moe API error!</b>",
        "not_found": "😔 <b>Anime not found!</b> Try another image",
        "quality_excellent": "🌟 <b>Excellent match</b>",
        "quality_good": "👍 <b>Good match</b>",
        "quality_medium": "🤔 <b>Medium match</b>",
        "quality_poor": "😐 <b>Poor match</b>"
    }
    
    strings_ru = {
        "searching": "🔍 <b>Ищу аниме...</b>",
        "error_no_reply": "❌ <b>Ответь на фото, GIF или стикер!</b>",
        "error_download": "❌ <b>Не удалось скачать изображение!</b>",
        "error_api": "❌ <b>Ошибка API Trace.moe!</b>",
        "not_found": "😔 <b>Аниме не найдено!</b> Попробуй другое изображение",
        "quality_excellent": "🌟 <b>Отличное совпадение</b>",
        "quality_good": "👍 <b>Хорошее совпадение</b>",
        "quality_medium": "🤔 <b>Среднее совпадение</b>",
        "quality_poor": "😐 <b>Слабое совпадение</b>"
    }

    def __init__(self):
        self.api_url = "https://api.trace.moe/search"
        self.shikimori_url = "https://shikimori.one/api/animes"

    async def client_ready(self, client, db):
        self.client = client
        self._db = db

    def get_quality_indicator(self, similarity: float) -> str:
        """Determine match quality"""
        if similarity >= 95:
            return self.strings["quality_excellent"]
        elif similarity >= 85:
            return self.strings["quality_good"]
        elif similarity >= 70:
            return self.strings["quality_medium"]
        else:
            return self.strings["quality_poor"]

    async def download_media_safely(self, media) -> Optional[bytes]:
        """Safe media download with retry"""
        for attempt in range(3):
            try:
                image_bytes = await self.client.download_media(media, bytes, thumb=-1)
                if image_bytes and len(image_bytes) > 0:
                    return image_bytes
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
                continue
        return None

    async def search_anime_api(self, image_bytes: bytes) -> Optional[Dict]:
        """Search through Trace.moe API"""
        params = {
            "anilistInfo": "1",
            "cutBorders": "1"
        }
        
        for attempt in range(3):
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=45),
                    headers={"User-Agent": "AnimeFinder/2.0"}
                ) as session:
                    data = aiohttp.FormData()
                    data.add_field(
                        "image", 
                        BytesIO(image_bytes), 
                        filename="anime_search.jpg", 
                        content_type="image/jpeg"
                    )
                    
                    async with session.post(self.api_url, params=params, data=data) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status == 429:  # penis
                            await asyncio.sleep(3 * (attempt + 1))
                            continue
                        else:
                            return None
                            
            except asyncio.TimeoutError:
                if attempt < 2:
                    await asyncio.sleep(2)
                continue
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
                continue
        
        return None

    async def get_russian_title(self, romaji: str, english: str) -> Optional[str]:
        """Get Russian title via Shikimori API"""
        if not romaji and not english:
            return None

        search_query = romaji if romaji and romaji != "Unknown" else english
        if not search_query or search_query == "Unknown":
            return None

        search_query = re.sub(r'[^\w\s-]', '', search_query).strip()
        
        try:
            await asyncio.sleep(0.5)
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "AnimeFinder/2.0"}
            ) as session:
                params = {
                    "search": search_query,
                    "limit": 5,
                    "order": "popularity"
                }
                
                async with session.get(self.shikimori_url, params=params) as resp:
                    if resp.status == 200:
                        results = await resp.json()
                        
                        for anime in results:
                            russian_title = anime.get("russian")
                            if russian_title and russian_title not in [romaji, english]:
                                return russian_title
                        return None
                    else:
                        return None
                        
        except Exception:
            return None

    def format_anime_result(self, result: Dict, russian_title: Optional[str] = None) -> str:
        """Format anime search result"""
        anilist = result.get("anilist", {})
        title = anilist.get("title", {})
        
        native = title.get("native", "Unknown")
        romaji = title.get("romaji", "Unknown")
        english = title.get("english", "Unknown")
        
        episode = result.get("episode", "Unknown")
        similarity = round(result.get("similarity", 0) * 100, 2)

        from_sec = int(result.get("from", 0))
        to_sec = int(result.get("to", 0))
        from_time = f"{from_sec // 60:02d}:{from_sec % 60:02d}"
        to_time = f"{to_sec // 60:02d}:{to_sec % 60:02d}"

        year = anilist.get("startDate", {}).get("year", "Unknown")
        status = anilist.get("status", "Unknown")
        genres = anilist.get("genres", [])
        
        quality = self.get_quality_indicator(similarity)
        
        response = f"{quality}\n\n"
        response += f"🎌 <b>Original:</b> <code>{native}</code>\n"
        response += f"🗾 <b>Romaji:</b> <code>{romaji}</code>\n"
        response += f"🇬🇧 <b>English:</b> <code>{english}</code>\n"
        
        if russian_title:
            response += f"🇷🇺 <b>Russian:</b> <code>{russian_title}</code>\n"
        
        response += f"\n📺 <b>Episode:</b> {episode}\n"
        response += f"⏰ <b>Time:</b> {from_time} - {to_time}\n"
        response += f"🎯 <b>Similarity:</b> {similarity}%\n"
        response += f"📅 <b>Year:</b> {year}\n"
        response += f"📊 <b>Status:</b> {status}\n"
        
        if genres:
            response += f"🎭 <b>Genres:</b> {', '.join(genres[:6])}\n"
        
        return response

    @loader.command(
        ru_doc="Найти аниме по изображению"
    )
    async def animefinder(self, message: Message):
        """Find anime by image"""
        reply = await message.get_reply_message()
        
        if not reply or not reply.media:
            await utils.answer(message, self.strings["error_no_reply"])
            return

        await utils.answer(message, self.strings["searching"])

        image_bytes = await self.download_media_safely(reply.media)
        if not image_bytes:
            await utils.answer(message, self.strings["error_download"])
            return

        api_result = await self.search_anime_api(image_bytes)
        if not api_result:
            await utils.answer(message, self.strings["error_api"])
            return

        if api_result.get("error"):
            await utils.answer(message, f"{self.strings['error_api']}\n<code>{api_result['error']}</code>")
            return

        results = api_result.get("result", [])
        if not results:
            await utils.answer(message, self.strings["not_found"])
            return

        main_result = results[0]
        similarity = round(main_result.get("similarity", 0) * 100, 2)
        
        anilist = main_result.get("anilist", {})
        title = anilist.get("title", {})
        romaji = title.get("romaji", "")
        english = title.get("english", "")
        
        russian_title = await self.get_russian_title(romaji, english)

        response = self.format_anime_result(main_result, russian_title)
 
        if similarity < 80 and len(results) > 1:
            response += f"\n\n📋 <b>Alternative results:</b>\n"
            for i, res in enumerate(results[1:4], 2):
                alt_title = res.get("anilist", {}).get("title", {}).get("romaji", "Unknown")
                alt_similarity = round(res.get("similarity", 0) * 100, 2)
                response += f"<b>{i}.</b> {alt_title} ({alt_similarity}%)\n"
        
        await utils.answer(message, response)