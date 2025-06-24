# scope: hikka_min 1.2.10
# meta developer: @your_username
# meta banner: https://i.ibb.co/0QxZvKb/module-watcher-banner.jpg
# requires: requests aiohttp

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import aiohttp
import requests
from hikkatl.types import Message
from hikkatl.tl.types import Channel, Chat, User

from .. import loader, utils

logger = logging.getLogger(__name__)


@loader.tds
class ModuleWatcherMod(loader.Module):
    """Отслеживает новые модули в GitHub репозиториях и уведомляет о них"""
    
    strings = {
        "name": "ModuleWatcher",
        "cfg_repos": "Список репозиториев для отслеживания",
        "cfg_channel": "Канал/чат для уведомлений",
        "cfg_interval": "Интервал проверки в секундах",
        "cfg_notification_template": "Шаблон уведомления",
        "repo_added": "✅ Репозиторий <code>{}</code> добавлен в отслеживание",
        "repo_removed": "❌ Репозиторий <code>{}</code> удален из отслеживания",
        "repo_not_found": "❌ Репозиторий <code>{}</code> не найден в списке",
        "invalid_repo": "❌ Неверная ссылка на репозиторий",
        "channel_set": "✅ Канал для уведомлений установлен: <b>{}</b>",
        "invalid_channel": "❌ Не удалось найти канал/чат или нет прав для отправки",
        "status_enabled": "✅ Отслеживание включено",
        "status_disabled": "❌ Отслеживание отключено",
        "current_repos": "📋 Отслеживаемые репозитории:",
        "no_repos": "❌ Нет отслеживаемых репозиториев",
        "new_module_title": "🆕 Новый модуль обнаружен!",
        "error_getting_info": "❌ Ошибка получения информации о модуле",
        "checking_repos": "🔍 Проверяю репозитории...",
        "check_complete": "✅ Проверка завершена",
        "provide_channel": "❌ Укажите канал/чат (@channel, t.me/channel или ID)",
        "test_message": "🔧 Тест отправки уведомлений ModuleWatcher",
        "no_config": "❌ Настройте репозитории и канал для уведомлений",
        "channel_help": "💡 Используйте: @channel, t.me/channel, channel_id или отправьте команду в нужном чате"
    }
    
    strings_ru = {
        "cfg_repos": "Список репозиториев для отслеживания",
        "cfg_channel": "Канал/чат для уведомлений", 
        "cfg_interval": "Интервал проверки в секундах",
        "cfg_notification_template": "Шаблон уведомления",
        "repo_added": "✅ Репозиторий <code>{}</code> добавлен в отслеживание",
        "repo_removed": "❌ Репозиторий <code>{}</code> удален из отслеживания",
        "repo_not_found": "❌ Репозиторий <code>{}</code> не найден в списке",
        "invalid_repo": "❌ Неверная ссылка на репозиторий",
        "channel_set": "✅ Канал для уведомлений установлен: <b>{}</b>",
        "invalid_channel": "❌ Не удалось найти канал/чат или нет прав для отправки",
        "status_enabled": "✅ Отслеживание включено",
        "status_disabled": "❌ Отслеживание отключено",
        "current_repos": "📋 Отслеживаемые репозитории:",
        "no_repos": "❌ Нет отслеживаемых репозиториев",
        "new_module_title": "🆕 Новый модуль обнаружен!",
        "error_getting_info": "❌ Ошибка получения информации о модуле",
        "checking_repos": "🔍 Проверяю репозитории...",
        "check_complete": "✅ Проверка завершена",
        "provide_channel": "❌ Укажите канал/чат (@channel, t.me/channel или ID)",
        "test_message": "🔧 Тест отправки уведомлений ModuleWatcher",
        "no_config": "❌ Настройте репозитории и канал для уведомлений",
        "channel_help": "💡 Используйте: @channel, t.me/channel, channel_id или отправьте команду в нужном чате"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "repos",
                [],
                lambda: self.strings("cfg_repos"),
                validator=loader.validators.Series(),
            ),
            loader.ConfigValue(
                "notification_channel",
                "",
                lambda: self.strings("cfg_channel"),
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "check_interval",
                300,
                lambda: self.strings("cfg_interval"),
                validator=loader.validators.Integer(minimum=60),
            ),
            loader.ConfigValue(
                "notification_template",
                "🆕 <b>Новый модуль обнаружен!</b>\n\n"
                "📦 <b>Название:</b> {name}\n"
                "👨‍💻 <b>Разработчик:</b> {developer}\n"
                "📝 <b>Описание:</b> {description}\n"
                "⚡ <b>Команды:</b> {commands}\n\n"
                "📥 <b>Установка:</b>\n<code>.dlm {url}</code>",
                lambda: self.strings("cfg_notification_template"),
                validator=loader.validators.String(),
            )
        )
        
        self._known_modules: Dict[str, Set[str]] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._notification_chat_id: Optional[int] = None

    async def client_ready(self, client, db):
        self._client = client
        self._db = db
        self._session = aiohttp.ClientSession()
        
        # Загружаем известные модули из базы данных
        self._known_modules = self.get("known_modules", {})
        
        # Получаем сохраненный ID канала
        self._notification_chat_id = self.get("notification_chat_id", None)
        
        # Запускаем цикл проверки
        if self.config["repos"] and self._notification_chat_id:
            self.check_loop.start()

    async def on_unload(self):
        if self._session:
            await self._session.close()
        
        # Сохраняем известные модули в базу данных
        self.set("known_modules", self._known_modules)
        if self._notification_chat_id:
            self.set("notification_chat_id", self._notification_chat_id)

    @loader.loop(interval=300, autostart=False)
    async def check_loop(self):
        """Цикл проверки новых модулей"""
        if not self.config["repos"] or not self._notification_chat_id:
            return
            
        interval = self.config["check_interval"]
        if interval != self.check_loop.interval:
            self.check_loop.interval = interval
            
        await self._check_repositories()

    async def _resolve_chat_id(self, chat_input: str) -> Optional[int]:
        """Определяет ID чата по различным форматам ввода"""
        try:
            # Если это уже числовой ID
            if chat_input.lstrip('-').isdigit():
                return int(chat_input)
            
            # Если это username (@channel)
            if chat_input.startswith('@'):
                username = chat_input[1:]
            elif 't.me/' in chat_input:
                username = chat_input.split('t.me/')[-1]
            else:
                username = chat_input
            
            # Пытаемся найти чат по username
            try:
                entity = await self._client.get_entity(username)
                return utils.get_chat_id(entity)
            except Exception:
                # Если не удалось найти по username, пытаемся как ID
                try:
                    return int(chat_input)
                except ValueError:
                    return None
                    
        except Exception as e:
            logger.error(f"Ошибка при определении ID чата: {e}")
            return None

    async def _check_repositories(self):
        """Проверяет все репозитории на наличие новых модулей"""
        for repo_url in self.config["repos"]:
            try:
                new_modules = await self._get_new_modules(repo_url)
                for module_info in new_modules:
                    await self._send_notification(module_info)
            except Exception as e:
                logger.error(f"Ошибка при проверке репозитория {repo_url}: {e}")

    async def _get_new_modules(self, repo_url: str) -> List[Dict]:
        """Получает новые модули из репозитория"""
        try:
            # Парсим URL репозитория
            parsed = urlparse(repo_url)
            if "github.com" not in parsed.netloc:
                return []
                
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) < 2:
                return []
                
            owner, repo = path_parts[0], path_parts[1]
            
            # API URL для получения содержимого репозитория
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
            
            async with self._session.get(api_url) as response:
                if response.status != 200:
                    logger.warning(f"Не удалось получить содержимое репозитория {repo_url}: {response.status}")
                    return []
                    
                files = await response.json()
                
            # Фильтруем Python файлы
            python_files = [f for f in files if f["name"].endswith(".py")]
            
            # Получаем известные модули для этого репозитория
            repo_key = f"{owner}/{repo}"
            known_files = self._known_modules.get(repo_key, set())
            
            new_modules = []
            current_files = set()
            
            for file_info in python_files:
                filename = file_info["name"]
                current_files.add(filename)
                
                if filename not in known_files:
                    # Новый модуль найден
                    module_info = await self._analyze_module(file_info["download_url"])
                    if module_info:
                        module_info["filename"] = filename
                        module_info["repo_url"] = repo_url
                        module_info["download_url"] = file_info["download_url"]
                        new_modules.append(module_info)
                        logger.info(f"Обнаружен новый модуль: {filename} в {repo_url}")
            
            # Обновляем список известных модулей
            self._known_modules[repo_key] = current_files
            
            return new_modules
            
        except Exception as e:
            logger.error(f"Ошибка при получении модулей из {repo_url}: {e}")
            return []

    async def _analyze_module(self, file_url: str) -> Optional[Dict]:
        """Анализирует модуль и извлекает информацию"""
        try:
            async with self._session.get(file_url) as response:
                if response.status != 200:
                    return None
                    
                content = await response.text()
                
            # Извлекаем информацию из кода модуля
            info = {
                "name": "Unknown",
                "developer": "@unknown",
                "description": "Описание недоступно",
                "commands": [],
                "banner": None
            }
            
            # Парсим мета-информацию
            meta_developer = re.search(r'# meta developer: (.+)', content)
            if meta_developer:
                info["developer"] = meta_developer.group(1).strip()
                
            meta_banner = re.search(r'# meta banner: (.+)', content)
            if meta_banner:
                info["banner"] = meta_banner.group(1).strip()
            
            # Ищем класс модуля
            class_match = re.search(r'class\s+(\w+)\(loader\.Module\):', content)
            if class_match:
                class_name = class_match.group(1)
                
                # Ищем docstring класса
                class_doc_match = re.search(
                    rf'class\s+{re.escape(class_name)}\(loader\.Module\):\s*"""(.+?)"""', 
                    content, 
                    re.DOTALL
                )
                if class_doc_match:
                    info["description"] = class_doc_match.group(1).strip()
                
                # Ищем strings для имени модуля
                strings_match = re.search(r'strings\s*=\s*\{[^}]*"name":\s*"([^"]+)"', content)
                if strings_match:
                    info["name"] = strings_match.group(1)
                else:
                    info["name"] = class_name.replace("Mod", "").replace("Module", "")
            
            # Ищем команды через @loader.command
            command_matches = re.findall(r'@loader\.command\([^)]*\)\s*async def (\w+)', content)
            for match in command_matches:
                if match.endswith('cmd'):
                    cmd_name = match[:-3]  # Убираем 'cmd' в конце
                    info["commands"].append(f".{cmd_name}")
                else:
                    info["commands"].append(f".{match}")
            
            # Альтернативный поиск команд через def xxxcmd
            alt_commands = re.findall(r'async def (\w+cmd)\(', content)
            for cmd in alt_commands:
                if cmd.endswith('cmd'):
                    cmd_name = cmd[:-3]
                    command = f".{cmd_name}"
                    if command not in info["commands"]:
                        info["commands"].append(command)
            
            return info
            
        except Exception as e:
            logger.error(f"Ошибка при анализе модуля {file_url}: {e}")
            return None

    async def _send_notification(self, module_info: Dict):
        """Отправляет уведомление о новом модуле"""
        try:
            if not self._notification_chat_id:
                return
                
            # Форматируем команды
            commands_str = ", ".join(module_info["commands"]) if module_info["commands"] else "Нет команд"
            
            # Форматируем сообщение
            message_text = self.config["notification_template"].format(
                name=utils.escape_html(module_info["name"]),
                developer=utils.escape_html(module_info["developer"]),
                description=utils.escape_html(module_info["description"]),
                commands=utils.escape_html(commands_str),
                url=module_info["download_url"],
                filename=utils.escape_html(module_info["filename"])
            )
            
            # Отправляем с баннером если есть
            if module_info.get("banner"):
                try:
                    await self._client.send_file(
                        self._notification_chat_id,
                        module_info["banner"],
                        caption=message_text,
                        parse_mode="html"
                    )
                    logger.info(f"Отправлено уведомление с баннером о модуле {module_info['name']}")
                except Exception as e:
                    logger.warning(f"Не удалось отправить с баннером: {e}")
                    # Если не удалось отправить с картинкой, отправляем текстом
                    await self._client.send_message(
                        self._notification_chat_id,
                        message_text,
                        parse_mode="html"
                    )
                    logger.info(f"Отправлено текстовое уведомление о модуле {module_info['name']}")
            else:
                await self._client.send_message(
                    self._notification_chat_id,
                    message_text,
                    parse_mode="html"
                )
                logger.info(f"Отправлено уведомление о модуле {module_info['name']}")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")

    @loader.command(
        ru_doc="Добавить репозиторий для отслеживания"
    )
    async def mwatchadd(self, message: Message):
        """Add repository to watch list"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "❌ Укажите URL репозитория")
            return
            
        # Проверяем валидность URL
        if "github.com" not in args or "/tree/" in args:
            await utils.answer(message, self.strings("invalid_repo"))
            return
            
        # Добавляем репозиторий
        repos = list(self.config["repos"])
        if args not in repos:
            repos.append(args)
            self.config["repos"] = repos
            await utils.answer(message, self.strings("repo_added").format(args))
        else:
            await utils.answer(message, "ℹ️ Репозиторий уже в списке отслеживания")

    @loader.command(
        ru_doc="Удалить репозиторий из отслеживания"
    )
    async def mwatchrm(self, message: Message):
        """Remove repository from watch list"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, "❌ Укажите URL репозитория")
            return
            
        repos = list(self.config["repos"])
        if args in repos:
            repos.remove(args)
            self.config["repos"] = repos
            await utils.answer(message, self.strings("repo_removed").format(args))
        else:
            await utils.answer(message, self.strings("repo_not_found").format(args))

    @loader.command(
        ru_doc="Показать список отслеживаемых репозиториев"
    )
    async def mwatchlist(self, message: Message):
        """Show list of watched repositories"""
        repos = self.config["repos"]
        if not repos:
            await utils.answer(message, self.strings("no_repos"))
            return
            
        repo_list = "\n".join([f"• <code>{repo}</code>" for repo in repos])
        await utils.answer(
            message,
            f"{self.strings('current_repos')}\n\n{repo_list}"
        )

    @loader.command(
        ru_doc="Установить канал для уведомлений"
    )
    async def mwatchch(self, message: Message):
        """Set notification channel"""
        args = utils.get_args_raw(message)
        
        # Если аргументы не указаны, используем текущий чат
        if not args:
            chat_id = utils.get_chat_id(message)
            self._notification_chat_id = chat_id
            self.set("notification_chat_id", chat_id)
            
            # Получаем информацию о чате
            try:
                chat = await self._client.get_entity(chat_id)
                chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', str(chat_id))
                await utils.answer(message, self.strings("channel_set").format(chat_name))
            except Exception:
                await utils.answer(message, self.strings("channel_set").format(chat_id))
            return
            
        # Определяем ID чата
        chat_id = await self._resolve_chat_id(args)
        if not chat_id:
            await utils.answer(
                message, 
                f"{self.strings('invalid_channel')}\n\n{self.strings('channel_help')}"
            )
            return
            
        try:
            # Проверяем, можем ли мы отправить сообщение в канал
            test_msg = await self._client.send_message(
                chat_id,
                self.strings("test_message")
            )
            await asyncio.sleep(2)
            await test_msg.delete()
            
            self._notification_chat_id = chat_id
            self.set("notification_chat_id", chat_id)
            
            # Получаем информацию о чате
            try:
                chat = await self._client.get_entity(chat_id)
                chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', str(chat_id))
                await utils.answer(message, self.strings("channel_set").format(chat_name))
            except Exception:
                await utils.answer(message, self.strings("channel_set").format(chat_id))
                
            # Запускаем отслеживание если все настроено
            if self.config["repos"] and not self.check_loop.status:
                self.check_loop.start()
                
        except Exception as e:
            logger.error(f"Ошибка при установке канала: {e}")
            await utils.answer(
                message, 
                f"{self.strings('invalid_channel')}\n\n{self.strings('channel_help')}"
            )

    @loader.command(
        ru_doc="Включить/выключить отслеживание"
    )
    async def mwatchtoggle(self, message: Message):
        """Toggle module watching"""
        if self.check_loop.status:
            self.check_loop.stop()
            await utils.answer(message, self.strings("status_disabled"))
        else:
            if not self.config["repos"] or not self._notification_chat_id:
                await utils.answer(message, self.strings("no_config"))
                return
            self.check_loop.start()
            await utils.answer(message, self.strings("status_enabled"))

    @loader.command(
        ru_doc="Проверить репозитории прямо сейчас"
    )
    async def mwatchcheck(self, message: Message):
        """Check repositories now"""
        if not self.config["repos"] or not self._notification_chat_id:
            await utils.answer(message, self.strings("no_config"))
            return
            
        msg = await utils.answer(message, self.strings("checking_repos"))
        await self._check_repositories()
        await utils.answer(msg, self.strings("check_complete"))

    @loader.command(
        ru_doc="Показать статус отслеживания"
    )
    async def mwatchstatus(self, message: Message):
        """Show watching status"""
        status = "✅ Включено" if self.check_loop.status else "❌ Выключено"
        repos_count = len(self.config["repos"])
        
        # Получаем название канала
        channel_info = "Не установлен"
        if self._notification_chat_id:
            try:
                chat = await self._client.get_entity(self._notification_chat_id)
                channel_info = getattr(chat, 'title', None) or getattr(chat, 'first_name', str(self._notification_chat_id))
            except Exception:
                channel_info = str(self._notification_chat_id)
        
        interval = self.config["check_interval"]
        
        text = (
            f"📊 <b>Статус ModuleWatcher</b>\n\n"
            f"🔄 <b>Отслеживание:</b> {status}\n"
            f"📋 <b>Репозиториев:</b> {repos_count}\n"
            f"📢 <b>Канал:</b> {channel_info}\n"
            f"⏱ <b>Интервал:</b> {interval} сек\n"
            f"💾 <b>Известно модулей:</b> {sum(len(modules) for modules in self._known_modules.values())}"
        )
        
        await utils.answer(message, text)