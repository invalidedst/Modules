# This file is a part of Heroku Userbot
# Code is licensed under CC-BY-NC-ND 4.0 unless otherwise specified
# + attribution 
# + non-commercial
# + no-derivatives

# You CANNOT edit this file without direct permission from the author.
# You can redistribute this file without any changes.

# meta developer: @Toxano_Modules
# scope: @Toxano_Modules

import asyncio
import logging
import datetime
from typing import Union
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class TimeInNickMod(loader.Module):
    """Показывает текущее время в никнейме и био с разными стилями шрифтов"""
    
    strings = {
        "name": "TimeInNick",
        "time_enabled": "⏰ Отображение времени в никнейме включено",
        "time_disabled": "⏰ Отображение времени в никнейме выключено",
        "bio_enabled": "⏰ Отображение времени в био включено", 
        "bio_disabled": "⏰ Отображение времени в био выключено",
        "invalid_delay": "⚠️ Неверный интервал обновления (должно быть 0-60 минут)",
        "cfg_timezone": "Часовой пояс (MSK/UTC/EST/CST/PST/etc)",
        "cfg_update": "Интервал обновления (0-60 минут, 0 = мгновенное обновление)",
        "cfg_nick_format": "Формат никнейма. Доступные переменные: {nickname}, {time}",
        "cfg_bio_format": "Формат био. Доступные переменные: {bio}, {time}",
        "error_updating": "⚠️ Ошибка обновления: {}",
        "error_timezone": "⚠️ Неверный часовой пояс. Используйте один из: MSK/UTC/EST/CST/PST",
        "already_enabled_bio": "⚠️ Время в био уже включено",
        "already_enabled_nick": "⚠️ Время в никнейме уже включено"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "TIMEZONE",
                "MSK",
                doc=lambda: self.strings("cfg_timezone"),
                validator=loader.validators.Choice(["MSK", "UTC", "EST", "CST", "PST"])
            ),
            loader.ConfigValue(
                "UPDATE_DELAY",
                0,
                doc=lambda: self.strings("cfg_update"),
                validator=loader.validators.Integer(minimum=0, maximum=60)
            ),
            loader.ConfigValue(
                "NICK_FORMAT",
                "{nickname} | {time}",
                doc=lambda: self.strings("cfg_nick_format"),
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "BIO_FORMAT",
                "{bio} | {time}",
                doc=lambda: self.strings("cfg_bio_format"),
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "FONT_STYLE",
                0,
                doc=lambda: (
                    "Стиль шрифта для времени:\n"
                    "0. 12:34 -> 12:34 (обычный)\n"
                    "1. 12:34 -> 『12:34』\n"
                    "2. 12:34 -> ⦅12⦆:⦅34⦆\n"
                    "3. 12:34 -> ➊➋:➌➍\n"
                    "4. 12:34 -> ⓵⓶:⓷⓸\n"
                    "5. 12:34 -> ①②:③④\n"
                    "6. 12:34 -> 𝟙𝟚:𝟛𝟜\n"
                    "7. 12:34 -> ¹²’³⁴\n"
                    "8. 12:34 -> ₁₂‚₃₄\n"
                    "9. 12:34 -> 1️⃣2️⃣:3️⃣4️⃣"
                ),
                validator=loader.validators.Integer(minimum=0, maximum=9)
            )
        )
        self.nick_active = False
        self.bio_active = False
        self.original_nick = None
        self.original_bio = None
        self.nick_task = None
        self.bio_task = None
        self.last_time = None

    async def client_ready(self, client, db):
        """Инициализация после загрузки модуля"""
        self.nick_active = self._db.get(self.strings["name"], "nick_active", False)
        self.bio_active = self._db.get(self.strings["name"], "bio_active", False)
        self.original_nick = self._db.get(self.strings["name"], "original_nick", None)
        self.original_bio = self._db.get(self.strings["name"], "original_bio", None)
        
        if self.nick_active and self.original_nick:
            self.nick_task = asyncio.create_task(self._update_nickname())
        
        if self.bio_active and self.original_bio:
            try:
                full_user = await self._client(GetFullUserRequest(self.tg_id))
                current_bio = full_user.full_user.about or ""
                if "|" in current_bio:
                    self.original_bio = current_bio.split("|")[0].strip()
                else:
                    self.original_bio = current_bio
                self.bio_task = asyncio.create_task(self._update_bio())
            except Exception as e:
                logger.exception("Failed to restore bio on startup")
                self.bio_active = False
                self._db.set(self.strings["name"], "bio_active", False)

    def apply_font(self, time_str: str, font_style: int) -> str:
        """Применяет выбранный стиль шрифта к строке времени"""
        fonts = {
            0: {str(i): str(i) for i in range(10)},
            1: dict({str(i): str(i) for i in range(10)}, **{":": ":", "start": "『", "end": "』"}),
            2: dict({str(i): str(i) for i in range(10)}, **{":": ":", "start": "⦅", "end": "⦆"}),
            3: {"0": "⓿", "1": "➊", "2": "➋", "3": "➌", "4": "➍", "5": "➎", "6": "➏", "7": "➐", "8": "➑", "9": "➒", ":": ":"},
            4: {"0": "⓪", "1": "⓵", "2": "⓶", "3": "⓷", "4": "⓸", "5": "⓹", "6": "⓺", "7": "⓻", "8": "⓼", "9": "⓽", ":": ":"},
            5: {"0": "⓪", "1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤", "6": "⑥", "7": "⑦", "8": "⑧", "9": "⑨", ":": ":"},
            6: {"0": "𝟘", "1": "𝟙", "2": "𝟚", "3": "𝟛", "4": "𝟜", "5": "𝟝", "6": "𝟞", "7": "𝟟", "8": "𝟠", "9": "𝟡", ":": ":"},
            7: {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", ":": "’"},
            8: {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉", ":": "‚"},
            9: {"0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", ":": ":"}
        }

        if font_style == 1:
            return f"『{time_str}』"
        elif font_style == 2:
            hours, minutes = time_str.split(":")
            return f"⦅{hours}⦆:⦅{minutes}⦆"
        elif font_style not in fonts:
            return time_str
        
        font = fonts[font_style]
        return "".join(font.get(char, char) for char in time_str)

    async def get_formatted_time(self) -> str:
        """Получает текущее время с учетом часового пояса и стиля шрифта"""
        now = datetime.datetime.now()
        timezone_offsets = {
            "MSK": 3, "EST": -5, "CST": -6,
            "PST": -8, "UTC": 0
        }
        
        timezone = self.config["TIMEZONE"].upper()
        if timezone not in timezone_offsets:
            logger.error(f"Invalid timezone: {timezone}")
            return now.strftime("%H:%M")
            
        offset = timezone_offsets[timezone]
        adjusted_time = now + datetime.timedelta(hours=offset)
        time_str = adjusted_time.strftime("%H:%M")
        
        return self.apply_font(time_str, self.config["FONT_STYLE"])

    async def _update_nickname(self) -> None:
        """Обновляет никнейм с текущим временем"""
        update_delay = self.config["UPDATE_DELAY"] * 60 if self.config["UPDATE_DELAY"] > 0 else 1
        
        while self.nick_active:
            try:
                current_time = await self.get_formatted_time()
                
                if current_time != self.last_time:
                    new_nick = self.config["NICK_FORMAT"].format(
                        nickname=self.original_nick,
                        time=current_time
                    )

                    await self._client(UpdateProfileRequest(
                        first_name=new_nick[:70]
                    ))
                    self.last_time = current_time

            except Exception as e:
                logger.exception(f"Error updating nickname: {e}")
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(update_delay)

    async def _update_bio(self) -> None:
        """Обновляет био с текущим временем"""
        update_delay = self.config["UPDATE_DELAY"] * 60 if self.config["UPDATE_DELAY"] > 0 else 1
        
        while self.bio_active:
            try:
                current_time = await self.get_formatted_time()
                
                if current_time != self.last_time:
                    new_bio = self.config["BIO_FORMAT"].format(
                        bio=self.original_bio.split("|")[0].strip(),
                        time=current_time
                    )

                    await self._client(UpdateProfileRequest(
                        about=new_bio[:70]
                    ))
                    self.last_time = current_time

            except Exception as e:
                logger.exception(f"Error updating bio: {e}")
                await asyncio.sleep(5)
                continue

            await asyncio.sleep(update_delay)

    @loader.command(
        ru_doc="Включить/выключить отображение времени в никнейме"
    )
    async def timenick(self, message: Message) -> None:
        """Включить/выключить отображение времени в никнейме"""
        if self.nick_active:
            self.nick_active = False
            if self.nick_task:
                self.nick_task.cancel()
            if self.original_nick:
                try:
                    await self._client(UpdateProfileRequest(
                        first_name=self.original_nick[:70]
                    ))
                except Exception as e:
                    logger.exception(f"Error restoring nickname: {e}")
                    await utils.answer(
                        message,
                        self.strings["error_updating"].format(str(e))
                    )
                    return
            
            self._db.set(self.strings["name"], "nick_active", False)
            self._db.set(self.strings["name"], "original_nick", None)
            
            await utils.answer(message, self.strings["time_disabled"])
            return
        
        try:
            me = await self._client.get_me()
            if "|" in me.first_name:
                await utils.answer(message, self.strings["already_enabled_nick"])
                return
                
            self.original_nick = me.first_name
            self.nick_active = True
            
            self._db.set(self.strings["name"], "nick_active", True)
            self._db.set(self.strings["name"], "original_nick", self.original_nick)
            
            self.nick_task = asyncio.create_task(self._update_nickname())
            await utils.answer(message, self.strings["time_enabled"])
        except Exception as e:
            self.nick_active = False
            logger.exception(f"Error enabling time in nickname: {e}")
            await utils.answer(
                message,
                self.strings["error_updating"].format(str(e))
            )

    @loader.command(
        ru_doc="Включить/выключить отображение времени в био"
    )
    async def timebio(self, message: Message) -> None:
        """Включить/выключить отображение времени в био"""
        if self.bio_active:
            self.bio_active = False
            if self.bio_task:
                self.bio_task.cancel()
            if self.original_bio:
                try:
                    await self._client(UpdateProfileRequest(
                        about=self.original_bio[:70]
                    ))
                except Exception as e:
                    logger.exception(f"Error restoring bio: {e}")
                    await utils.answer(
                        message,
                        self.strings["error_updating"].format(str(e))
                    )
                    return

            self._db.set(self.strings["name"], "bio_active", False)
            self._db.set(self.strings["name"], "original_bio", None)

            await utils.answer(message, self.strings["bio_disabled"])
            return

        try:
            full_user = await self._client(GetFullUserRequest(self.tg_id))
            current_bio = full_user.full_user.about or ""
            
            if "|" in current_bio:
                await utils.answer(message, self.strings["already_enabled_bio"])
                return
                
            self.original_bio = current_bio
            self.bio_active = True

            self._db.set(self.strings["name"], "bio_active", True) 
            self._db.set(self.strings["name"], "original_bio", self.original_bio)

            self.bio_task = asyncio.create_task(self._update_bio())
            await utils.answer(message, self.strings["bio_enabled"])
        except Exception as e:
            self.bio_active = False
            logger.exception(f"Error enabling time in bio: {e}")
            await utils.answer(
                message,
                self.strings["error_updating"].format(str(e))
            )

    async def on_unload(self) -> None:
        """Вызывается при выгрузке модуля"""
        try:
            if self.nick_active:
                self.nick_active = False
                if self.nick_task:
                    self.nick_task.cancel()
                if self.original_nick:
                    await self._client(UpdateProfileRequest(
                        first_name=self.original_nick[:70]
                    ))

            if self.bio_active:
                self.bio_active = False
                if self.bio_task:
                    self.bio_task.cancel()
                if self.original_bio:
                    await self._client(UpdateProfileRequest(
                        about=self.original_bio[:70]
                    ))

        except Exception as e:
            logger.exception(f"Error during unload: {e}")
        finally:
            self._db.set(self.strings["name"], "nick_active", False)
            self._db.set(self.strings["name"], "original_nick", None)
            self._db.set(self.strings["name"], "bio_active", False)
            self._db.set(self.strings["name"], "original_bio", None)
