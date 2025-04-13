# You CANNOT edit this file without direct permission from the author.
# You can redistribute this file without any changes.

# meta developer: @Toxano_Modules
# scope: @Toxano
# scope: @Toxano_Modulesimport 

import asyncio
import logging
from telethon.tl.functions.account import UpdateProfileRequest
from .. import loader, utils
from telethon import TelegramClient

logger = logging.getLogger(__name__)

@loader.tds
class TimeInNickMod(loader.Module):
    """Показывает текущее время в никнейме с поддержкой часовых поясов"""
    
    strings = {
        "name": "ВремяВНике",
        "time_enabled": "⏰ Отображение времени в нике включено",
        "time_disabled": "⏰ Отображение времени в нике выключено", 
        "invalid_delay": "⚠️ Неверный интервал обновления (должен быть 1-60 минут)",
        "night_mode_enabled": "🌙 Ночной режим включен",
        "night_mode_disabled": "🌅 Ночной режим выключен",
        "cfg_timezone": "Часовой пояс (MSK/UTC/EST/CST/PST/etc)",
        "cfg_update": "Интервал обновления ника (1-60 минут)",
        "cfg_night": "Отключать обновления в ночное время (00:00-06:00)",
        "cfg_night_start": "Время начала ночного режима (ЧЧ:ММ)",
        "cfg_night_end": "Время окончания ночного режима (ЧЧ:ММ)", 
        "cfg_format": "Формат ника. Доступные переменные: {nickname}, {time}"
    }

    strings_ru = {
        "name": "ВремяВНике",
        "_cmd_doc_updatenick": "Включить/выключить отображение времени в никнейме",
        "_cls_doc": "Показывает текущее время в никнейме с поддержкой часовых поясов"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "TIMEZONE", "MSK", lambda: self.strings("cfg_timezone"),
            "UPDATE_DELAY", 1, lambda: self.strings("cfg_update"),
            "NIGHT_MODE", True, lambda: self.strings("cfg_night"),
            "NIGHT_START", "00:00", lambda: self.strings("cfg_night_start"),
            "NIGHT_END", "06:00", lambda: self.strings("cfg_night_end"),
            "TIME_FORMAT", "{nickname} | {time}", lambda: self.strings("cfg_format")
        )
        self.active = False
        self.original_nick = None
        self.task = None

    async def client_ready(self, client: TelegramClient, db):
        """Вызывается при загрузке модуля"""
        self._client = client

    async def updatenickcmd(self, message):
        """Включить/выключить отображение времени в никнейме"""
        if self.active:
            self.active = False
            if self.task:
                self.task.cancel()
            if self.original_nick:
                try:
                    await self._client(UpdateProfileRequest(
                        first_name=self.original_nick
                    ))
                except Exception as e:
                    logger.error(f"Ошибка при обновлении ника: {e}")
            await utils.answer(message, self.strings["time_disabled"])
            return
        
        self.active = True
        me = await self._client.get_me()
        self.original_nick = me.first_name
        await utils.answer(message, self.strings["time_enabled"])
        
        # Запускаем обновление в отдельной таске
        self.task = asyncio.create_task(self.update_nickname())

    async def update_nickname(self):
        """Обновляет никнейм с текущим временем"""
        while self.active:
            try:
                now = datetime.datetime.now()
                
                # Проверка ночного режима
                if self.config["NIGHT_MODE"]:
                    night_start = datetime.datetime.strptime(self.config["NIGHT_START"], "%H:%M").time()
                    night_end = datetime.datetime.strptime(self.config["NIGHT_END"], "%H:%M").time() 
                    current_time = now.time()
                    
                    if night_start <= current_time <= night_end:
                        await asyncio.sleep(60)
                        continue

                # Форматирование времени согласно часовому поясу
                if self.config["TIMEZONE"] == "MSK":
                    time_str = (now + datetime.timedelta(hours=3)).strftime("%H:%M")
                elif self.config["TIMEZONE"] == "EST":
                    time_str = (now - datetime.timedelta(hours=5)).strftime("%H:%M")
                else:
                    time_str = now.strftime("%H:%M")

                new_nick = self.config["TIME_FORMAT"].format(
                    nickname=self.original_nick,
                    time=time_str
                )

                await self._client(UpdateProfileRequest(
                    first_name=new_nick
                ))

            except Exception as e:
                logger.error(f"Ошибка при обновлении ника: {e}")

            # Ждем 1 минуту перед следующим обновлением
            await asyncio.sleep(60)

    async def on_unload(self):
        """Вызывается при выгрузке модуля"""
        if self.task:
            self.task.cancel()
