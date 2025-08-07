import asyncio
import aiohttp
import logging
import time
from typing import Optional, Dict, List, Any
from herokutl.types import Message
from .. import loader, utils

@loader.tds
class VoiceToxanoMod(loader.Module):
    """Музыка, видео и фото в голосовом чате с плейлистами и панелью управления"""

    strings = {
        "name": "VoiceToxano",
        "processing": "🔄 <b>Обрабатываю запрос...</b>",
        "success": "✅ <b>Операция выполнена успешно!</b>",
        "error_generic": "❌ <b>Произошла ошибка:</b> <code>{error}</code>",
        "error_network": "🌐 <b>Сетевая ошибка:</b> <code>{error}</code>",
        "error_api": "🔌 <b>Ошибка API:</b> <code>{error}</code>",
        "error_timeout": "⏱️ <b>Превышено время ожидания</b>",
        "error_not_found": "🔍 <b>Данные не найдены</b>",
        "invalid_args": "⚠️ <b>Неверные аргументы</b>",
        "config_desc_repeat": "Включить повтор трека",
        "config_desc_volume": "Громкость воспроизведения (0-200)",
        "config_desc_timeout": "Таймаут сетевых операций (сек)",
        "config_desc_max_playlist": "Максимальный размер плейлиста"
    }

    strings_ru = {
        "processing": "🔄 <b>Обрабатываю запрос...</b>",
        "success": "✅ <b>Операция выполнена успешно!</b>",
        "error_generic": "❌ <b>Произошла ошибка:</b> <code>{error}</code>",
        "error_network": "🌐 <b>Сетевая ошибка:</b> <code>{error}</code>",
        "error_api": "🔌 <b>Ошибка API:</b> <code>{error}</code>",
        "error_timeout": "⏱️ <b>Превышено время ожидания</b>",
        "error_not_found": "🔍 <b>Данные не найдены</b>",
        "invalid_args": "⚠️ <b>Неверные аргументы</b>",
        "config_desc_repeat": "Включить повтор трека",
        "config_desc_volume": "Громкость воспроизведения (0-200)",
        "config_desc_timeout": "Таймаут сетевых операций (сек)",
        "config_desc_max_playlist": "Максимальный размер плейлиста"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "repeat",
                False,
                lambda: self.strings("config_desc_repeat"),
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "volume",
                100,
                lambda: self.strings("config_desc_volume"),
                validator=loader.validators.Integer(minimum=0, maximum=200)
            ),
            loader.ConfigValue(
                "timeout",
                30,
                lambda: self.strings("config_desc_timeout"),
                validator=loader.validators.Integer(minimum=5, maximum=120)
            ),
            loader.ConfigValue(
                "max_playlist",
                50,
                lambda: self.strings("config_desc_max_playlist"),
                validator=loader.validators.Integer(minimum=1, maximum=200)
            )
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._task_lock = asyncio.Lock()
        self._playlist: List[Dict[str, Any]] = []
        self._current_track: Optional[Dict[str, Any]] = None
        self._is_playing = False
        self._panel_message_id: Optional[int] = None
        self._stats = {
            "tracks_played": 0,
            "errors": 0,
            "cache_hits": 0,
            "start_time": time.time()
        }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config["timeout"]),
            headers={"User-Agent": f"{self.strings['name']}/1.0"}
        )
        self._cleanup_task = asyncio.create_task(self._cache_cleanup_loop())
        saved_data = self._db.get(self.strings["name"], "module_data", {})
        if self._validate_saved_data(saved_data):
            self._restore_state(saved_data)

    async def on_unload(self):
        self._save_state()
        if self._session:
            await self._session.close()
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
        for task in asyncio.all_tasks():
            if task.get_name().startswith(f"{self.strings['name']}_"):
                task.cancel()