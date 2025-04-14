import asyncio
import logging
import datetime
from telethon.tl.functions.account import UpdateProfileRequest
from .. import loader, utils
from telethon import TelegramClient

logger = logging.getLogger(__name__)

@loader.tds
class TimeInNickMod(loader.Module):
    """Shows current time in nickname with timezone support"""
    
    strings = {
        "name": "TimeInNick",
        "time_enabled": "⏰ Time display in nickname enabled",
        "time_disabled": "⏰ Time display in nickname disabled", 
        "invalid_delay": "⚠️ Invalid update interval (should be 1-60 minutes)",
        "night_mode_enabled": "🌙 Night mode enabled",
        "night_mode_disabled": "🌅 Night mode disabled",
        "cfg_timezone": "Timezone (MSK/UTC/EST/CST/PST/etc)",
        "cfg_update": "Nickname update interval (1-60 minutes)",
        "cfg_night": "Disable updates during night time (00:00-06:00)",
        "cfg_night_start": "Night mode start time (HH:MM)",
        "cfg_night_end": "Night mode end time (HH:MM)", 
        "cfg_format": "Nickname format. Available variables: {nickname}, {time}",
        "error_updating": "⚠️ Error updating nickname: {}"
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
        self._client = client

    @loader.command(
        ru_doc="Включить/выключить отображение времени в никнейме"
    )
    async def timenick(self, message):
        """Toggle time display in nickname"""
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
                    logger.error(f"Error restoring nickname: {e}")
                    await utils.answer(
                        message,
                        self.strings["error_updating"].format(str(e))
                    )
                    return
            await utils.answer(message, self.strings["time_disabled"])
            return
        
        self.active = True
        me = await self._client.get_me()
        self.original_nick = me.first_name
        await utils.answer(message, self.strings["time_enabled"])
        self.task = asyncio.create_task(self.update_nickname())

    async def get_formatted_time(self):
        """Get current time formatted according to timezone settings"""
        now = datetime.datetime.now()
        timezone_offsets = {
            "MSK": 3,
            "EST": -5,
            "CST": -6,
            "PST": -8,
            "UTC": 0
        }
        
        offset = timezone_offsets.get(self.config["TIMEZONE"].upper(), 0)
        adjusted_time = now + datetime.timedelta(hours=offset)
        return adjusted_time.strftime("%H:%M")

    async def update_nickname(self):
        """Updates nickname with current time"""
        while self.active:
            try:
                now = datetime.datetime.now()
                
                if self.config["NIGHT_MODE"]:
                    night_start = datetime.datetime.strptime(
                        self.config["NIGHT_START"], 
                        "%H:%M"
                    ).time()
                    night_end = datetime.datetime.strptime(
                        self.config["NIGHT_END"], 
                        "%H:%M"
                    ).time()
                    current_time = now.time()
                    
                    if night_start <= current_time <= night_end:
                        await asyncio.sleep(60)
                        continue

                time_str = await self.get_formatted_time()
                new_nick = self.config["TIME_FORMAT"].format(
                    nickname=self.original_nick,
                    time=time_str
                )

                await self._client(UpdateProfileRequest(
                    first_name=new_nick
                ))

            except Exception as e:
                logger.error(f"Error updating nickname: {e}")

            await asyncio.sleep(60 * self.config["UPDATE_DELAY"])

    async def on_unload(self):
        """Called when module is being unloaded"""
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
                    logger.error(f"Error restoring nickname during unload: {e}")
