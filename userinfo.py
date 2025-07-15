#  _____                          
# |_   _|____  ____ _ _ __   ___  
#   | |/ _ \ \/ / _` | '_ \ / _ \ 
#   | | (_) >  < (_| | | | | (_) |
#   |_|\___/_/\_\__,_|_| |_|\___/ 
#                              
# meta banner: https://i.ibb.co/3yNfKRLL/image-10490.jpg
# meta developer: @toxano_modules 
# scope: @toxano_modules

import asyncio
from datetime import datetime
from herokutl.types import Message
from .. import loader, utils
import re

@loader.tds
class UserInfoMod(loader.Module):
    """Модуль для получения информации об аккаунте пользователя"""

    strings = {
        "name": "UserInfo",
        "processing": "🔍 <b>Получаю информацию о пользователе...</b>",
        "user_not_found": "❌ <b>Пользователь не найден!</b>",
        "invalid_args": "❌ <b>Использование:</b> <code>{}check @username</code> или <code>{}check user_id</code>\n💡 <b>Также можно использовать в ответ на сообщение</b>",
        "error": "❌ <b>Ошибка при получении информации:</b> <code>{}</code>",
        "no_user": "❌ <b>Не удалось определить пользователя</b>",
        "deleted_account": "🗑 <b>Удаленный аккаунт</b>",
        "premium_yes": "⭐ Да",
        "premium_no": "❌ Нет",
        "bot_yes": "🤖 Да",
        "bot_no": "👤 Нет",
        "verified_yes": "✅ Да",
        "verified_no": "❌ Нет",
        "restricted_yes": "🚫 Да",
        "restricted_no": "✅ Нет",
        "not_set": "📝 Не указан",
        "unknown": "❓ Неизвестно"
    }

    strings_ru = {
        "processing": "🔍 <b>Получаю информацию о пользователе...</b>",
        "user_not_found": "❌ <b>Пользователь не найден!</b>",
        "invalid_args": "❌ <b>Использование:</b> <code>{}check @username</code> или <code>{}check user_id</code>\n💡 <b>Также можно использовать в ответ на сообщение</b>",
        "error": "❌ <b>Ошибка при получении информации:</b> <code>{}</code>",
        "no_user": "❌ <b>Не удалось определить пользователя</b>",
        "deleted_account": "🗑 <b>Удаленный аккаунт</b>",
        "premium_yes": "⭐ Да",
        "premium_no": "❌ Нет",
        "bot_yes": "🤖 Да",
        "bot_no": "👤 Нет",
        "verified_yes": "✅ Да",
        "verified_no": "❌ Нет",
        "restricted_yes": "🚫 Да",
        "restricted_no": "✅ Нет",
        "not_set": "📝 Не указан",
        "unknown": "❓ Неизвестно"
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db



    def format_user_info(self, user, full_user=None):
        """Форматирует информацию о пользователе"""
        if not user:
            return self.strings["deleted_account"]

        # Создаем красивый интерфейс с цитированием
        info = f"<blockquote><b>📋 Информация о пользователе</b></blockquote>\n\n"
        
        # ID и основная информация
        if hasattr(user, 'id'):
            info += f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        
        # Имя
        if hasattr(user, 'first_name') and user.first_name:
            info += f"👤 <b>Имя:</b> {utils.escape_html(user.first_name)}"
            if hasattr(user, 'last_name') and user.last_name:
                info += f" {utils.escape_html(user.last_name)}"
            info += "\n"
        
        # Юзернейм
        if hasattr(user, 'username') and user.username:
            info += f"📝 <b>Юзернейм:</b> @{user.username}\n"
        else:
            info += f"📝 <b>Юзернейм:</b> {self.strings['not_set']}\n"
        
        # Статусы (только если доступны)
        if hasattr(user, 'bot'):
            info += f"🤖 <b>Бот:</b> {self.strings['bot_yes'] if user.bot else self.strings['bot_no']}\n"
        
        if hasattr(user, 'verified'):
            info += f"✅ <b>Верифицирован:</b> {self.strings['verified_yes'] if user.verified else self.strings['verified_no']}\n"
        
        if hasattr(user, 'premium'):
            info += f"⭐ <b>Премиум:</b> {self.strings['premium_yes'] if user.premium else self.strings['premium_no']}\n"
        
        if hasattr(user, 'restricted'):
            info += f"🚫 <b>Ограничен:</b> {self.strings['restricted_yes'] if user.restricted else self.strings['restricted_no']}\n"
        
        # Последняя активность
        if hasattr(user, 'status') and user.status:
            status_text = self.format_user_status(user.status)
            info += f"🟢 <b>Статус:</b> {status_text}\n"
        
        # Дополнительная информация, если доступна
        if hasattr(user, 'phone') and user.phone:
            info += f"📱 <b>Телефон:</b> +{user.phone}\n"
        
        return info



    def format_user_status(self, status):
        """Форматирует статус пользователя"""
        status_type = type(status).__name__
        
        if status_type == "UserStatusOnline":
            return "🟢 Онлайн"
        elif status_type == "UserStatusOffline":
            if hasattr(status, 'was_online'):
                offline_time = datetime.fromtimestamp(status.was_online.timestamp())
                return f"🔴 Был(а) в сети: {offline_time.strftime('%d.%m.%Y %H:%M')}"
            return "🔴 Не в сети"
        elif status_type == "UserStatusRecently":
            return "🟡 Недавно"
        elif status_type == "UserStatusLastWeek":
            return "🟠 На этой неделе"
        elif status_type == "UserStatusLastMonth":
            return "🟤 В этом месяце"
        else:
            return "⚪ Неизвестно"

    async def get_user_entity(self, identifier):
        """Получает пользователя по username или ID"""
        try:
            if isinstance(identifier, str):
                # Убираем @ если есть
                if identifier.startswith('@'):
                    identifier = identifier[1:]
                
                # Проверяем, является ли это числом (ID)
                if identifier.isdigit():
                    user_id = int(identifier)
                    return await self._client.get_entity(user_id)
                else:
                    # Это username
                    return await self._client.get_entity(identifier)
            else:
                # Это уже ID
                return await self._client.get_entity(identifier)
        except Exception as e:
            return None

    @loader.command(
        ru_doc="<@username или ID> - Получить информацию о пользователе"
    )
    async def check(self, message: Message):
        """<@username или ID> - Получить информацию о пользователе"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        
        user_entity = None
        
        # Проверяем есть ли реплай
        if reply and reply.sender:
            user_entity = reply.sender
        # Если есть аргументы, пробуем найти пользователя
        elif args:
            await utils.answer(message, self.strings["processing"])
            user_entity = await self.get_user_entity(args.split()[0])
            if not user_entity:
                await utils.answer(message, self.strings["user_not_found"])
                return
        # Если нет реплая, используем отправителя текущего сообщения
        elif message.sender:
            user_entity = message.sender
        else:
            prefix = getattr(self, 'get_prefix', lambda: '.')()
            await utils.answer(
                message, 
                self.strings["invalid_args"].format(prefix, prefix)
            )
            return
        
        if not user_entity:
            await utils.answer(message, self.strings["user_not_found"])
            return
        
        # Показываем процесс (если не показывался ранее)
        if not args:
            await utils.answer(message, self.strings["processing"])
        
        try:
            # Форматируем информацию
            info_text = self.format_user_info(user_entity, None)
            
            # Пытаемся получить аватарку
            try:
                photo = await self._client.download_profile_photo(user_entity, bytes)
                if photo:
                    # Отправляем фото с информацией
                    await self._client.send_file(
                        message.peer_id,
                        photo,
                        caption=info_text,
                        parse_mode='html',
                        reply_to=message.reply_to_msg_id
                    )
                    # Удаляем сообщение "Получаю информацию..."
                    await message.delete()
                else:
                    # Если нет фото, отправляем просто текст
                    await utils.answer(message, info_text)
            except Exception:
                # Если не удалось получить фото, отправляем просто текст
                await utils.answer(message, info_text)
                
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))