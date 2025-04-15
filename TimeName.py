"""
    ▀█▀ █▀█ █▀▀█ █▀▀█ █▀▀▄ █▀▀█ 
    ░█░ █░█ █▄▄█ █▄▄█ █░░█ █░░█ 
    ░▀░ ▀▀▀ ▀░░▀ ▀░░▀ ▀░░▀ ▀▀▀▀
"""

# meta developer: @hikariatama
# meta banner: https://img.example.com/banner.jpg
# meta pic: https://img.example.com/pic.jpg
# scope: inline
# scope: hikka_min 1.2.10

import asyncio
import logging
import datetime
from typing import Union
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.types import Message
from .. import loader, utils

logger = logging.getLogger(__name__)

@loader.tds
class TimeInNickMod(loader.Module):
    """Показывает текущее время в никнейме с разными стилями шрифтов"""
    
    strings = {
        "name": "TimeInNick",
        "time_enabled": "⏰ Отображение времени в никнейме включено",
        "time_disabled": "⏰ Отображение времени в никнейме выключено", 
        "invalid_delay": "⚠️ Неверный интервал обновления (должно быть 1-60 минут)",
        "cfg_timezone": "Часовой пояс (MSK/UTC/EST/CST/PST/etc)",
        "cfg_update": "Интервал обновления никнейма (1-60 минут)",
        "cfg_format": "Формат никнейма. Доступные переменные: {nickname}, {time}",
        "error_updating": "⚠️ Ошибка обновления никнейма: {}",
        "error_timezone": "⚠️ Неверный часовой пояс. Используйте один из: MSK/UTC/EST/CST/PST"
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
                1,
                doc=lambda: self.strings("cfg_update"),
                validator=loader.validators.Integer(minimum=1, maximum=60)
            ),
            loader.ConfigValue(
                "TIME_FORMAT",
                "{nickname} | {time}",
                doc=lambda: self.strings("cfg_format"),
                validator=loader.validators.String()
            ),
            loader.ConfigValue(
                "FONT_STYLE",
                0,
                doc=lambda: (
                    "Стиль шрифта для времени в никнейме:\n"
                    "0. 12:34 -> 12:34 (обычный)\n"
                    "1. 12:34 -> 『12:34』\n"
                    "2. 12:34 -> ⦅12⦆:⦅34⦆\n"
                    "3. 12:34 -> ➊➋:➌➍\n"
                    "4. 12:34 -> ⓵⓶:⓷⓸\n"
                    "5. 12:34 -> ①②:③④\n"
                    "6. 12:34 -> 𝟙𝟚:𝟛𝟜\n"
                    "7. 12:34 -> ¹²:³⁴ (верхний индекс)\n"
                    "8. 12:34 -> ₁₂:₃₄ (нижний индекс)"
                ),
                validator=loader.validators.Integer(minimum=0, maximum=8)
            )
        )
        self.active = False
        self.original_nick = None
        self.task = None
        self.last_time = None

    async def client_ready(self, client, db):
        """Инициализация после загрузки модуля"""
        self.active = self._db.get(self.strings["name"], "active", False)
        self.original_nick = self._db.get(self.strings["name"], "original_nick", None)
        
        if self.active and self.original_nick:
            self.task = asyncio.create_task(self._update_nickname())

    def apply_font(self, time_str: str, font_style: int) -> str:
        """Применяет выбранный стиль шрифта к строке времени"""
        fonts = {
            0: {str(i): str(i) for i in range(10)},
            1: {str(i): f"『{i}』" for i in range(10)},
            2: {str(i): f"⦅{i}⦆" for i in range(10)},
            3: {"0": "⓿", "1": "➊", "2": "➋", "3": "➌", "4": "➍",
                "5": "➎", "6": "➏", "7": "➐", "8": "➑", "9": "➒"},
            4: {"0": "⓪", "1": "⓵", "2": "⓶", "3": "⓷", "4": "⓸",
                "5": "⓹", "6": "⓺", "7": "⓻", "8": "⓼", "9": "⓽"},
            5: {"0": "⓪", "1": "①", "2": "②", "3": "③", "4": "④",
                "5": "⑤", "6": "⑥", "7": "⑦", "8": "⑧", "9": "⑨"},
            6: {"0": "𝟘", "1": "𝟙", "2": "𝟚", "3": "𝟛", "4": "𝟜",
                "5": "𝟝", "6": "𝟞", "7": "𝟟", "8": "𝟠", "9": "𝟡"},
            7: {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
                "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"},
            8: {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
                "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}
        }

        if font_style not in fonts:
            return time_str

        font = fonts[font_style]
        font[":"] = ":"
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
        while self.active:
            try:
                current_time = await self.get_formatted_time()
                
                if current_time == self.last_time:
                    await asyncio.sleep(30)
                    continue

                new_nick = self.config["TIME_FORMAT"].format(
                    nickname=self.original_nick,
                    time=current_time
                )

                me = await self._client.get_me()
                if me.first_name != new_nick:
                    await self._client(UpdateProfileRequest(
                        first_name=new_nick[:70]  # Telegram limit
                    ))
                    self.last_time = current_time

            except Exception as e:
                logger.exception(f"Error updating nickname: {e}")
                await asyncio.sleep(5)  # Prevent flood on error
                continue

            await asyncio.sleep(60 * self.config["UPDATE_DELAY"])

    @loader.command(
        ru_doc="Включить/выключить отображение времени в никнейме"
    )
    async def timenick(self, message: Message) -> None:
        """Включить/выключить отображение времени в никнейме"""
        if self.active:
            self.active = False
            if self.task:
                self.task.cancel()
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
            
            self._db.set(self.strings["name"], "active", False)
            self._db.set(self.strings["name"], "original_nick", None)
            
            await utils.answer(message, self.strings["time_disabled"])
            return
        
        try:
            me = await self._client.get_me()
            self.original_nick = me.first_name
            self.active = True
            
            self._db.set(self.strings["name"], "active", True)
            self._db.set(self.strings["name"], "original_nick", self.original_nick)
            
            self.task = asyncio.create_task(self._update_nickname())
            await utils.answer(message, self.strings["time_enabled"])
        except Exception as e:
            self.active = False
            logger.exception(f"Error enabling time in nickname: {e}")
            await utils.answer(
                message,
                self.strings["error_updating"].format(str(e))
            )

    async def on_unload(self) -> None:
        """Вызывается при выгрузке модуля"""
        try:
            if self.active:
                self.active = False
                if self.task:
                    self.task.cancel()
                if self.original_nick:
                    await self._client(UpdateProfileRequest(
                        first_name=self.original_nick[:70]
                    ))
        except Exception as e:
            logger.exception(f"Error during unload: {e}")
