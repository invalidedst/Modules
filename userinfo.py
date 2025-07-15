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

@loader.tds
class UserInfoMod(loader.Module):
    """Модуль для получения информации об аккаунте пользователя"""

    strings = {
        "name": "UserInfo",
        "processing": "🔍 <b>Получаю информацию о пользователе...</b>",
        "user_not_found": "❌ <b>Пользователь не найден!</b>",
        "invalid_args": "❌ <b>Использование:</b> <code>{}check @username</code> или <code>{}check user_id</code>\n💡 <b>Также можно использовать в ответ на сообщение</b>",
        "flood_wait": "⏳ <b>Слишком много запросов! Подождите {} секунд</b>",
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
        "scam_yes": "⚠️ Да",
        "scam_no": "✅ Нет",
        "fake_yes": "🆔 Да",
        "fake_no": "✅ Нет",
        "hidden": "🔒 Скрыт",
        "not_set": "📝 Не указан",
        "unknown": "❓ Неизвестно"
    }

    strings_ru = {
        "processing": "🔍 <b>Получаю информацию о пользователе...</b>",
        "user_not_found": "❌ <b>Пользователь не найден!</b>",
        "invalid_args": "❌ <b>Использование:</b> <code>{}check @username</code> или <code>{}check user_id</code>\n💡 <b>Также можно использовать в ответ на сообщение</b>",
        "flood_wait": "⏳ <b>Слишком много запросов! Подождите {} секунд</b>",
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
        "scam_yes": "⚠️ Да",
        "scam_no": "✅ Нет",
        "fake_yes": "🆔 Да",
        "fake_no": "✅ Нет",
        "hidden": "🔒 Скрыт",
        "not_set": "📝 Не указан",
        "unknown": "❓ Неизвестно"
    }

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    def format_date(self, timestamp):
        """Форматирует дату в читаемый вид"""
        if not timestamp:
            return self.strings["unknown"]
        
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%d.%m.%Y %H:%M:%S")
        except:
            return self.strings["unknown"]

    def format_user_info(self, user, full_user=None):
        """Форматирует информацию о пользователе"""
        if not user:
            return self.strings["deleted_account"]

        # Базовая информация
        info = f"👤 <b>Информация о пользователе:</b>\n\n"
        
        # ID и основная информация
        if hasattr(user, 'id'):
            info += f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        
        # Имя
        if hasattr(user, 'first_name') and user.first_name:
            info += f"👋 <b>Имя:</b> {utils.escape_html(user.first_name)}"
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
        
        if hasattr(user, 'scam'):
            info += f"⚠️ <b>Скам:</b> {self.strings['scam_yes'] if user.scam else self.strings['scam_no']}\n"
        
        if hasattr(user, 'fake'):
            info += f"🆔 <b>Фейк:</b> {self.strings['fake_yes'] if user.fake else self.strings['fake_no']}\n"
        
        # Дата создания аккаунта (приблизительная)
        if hasattr(user, 'id') and user.id:
            approx_date = self.estimate_registration_date(user.id)
            info += f"📅 <b>Примерная дата создания:</b> {approx_date}\n"
        
        # Последняя активность
        if hasattr(user, 'status') and user.status:
            status_text = self.format_user_status(user.status)
            info += f"🟢 <b>Статус:</b> {status_text}\n"
        
        # Дополнительная информация, если доступна
        if hasattr(user, 'phone') and user.phone:
            info += f"📱 <b>Телефон:</b> +{user.phone}\n"
        
        if hasattr(user, 'about') and user.about:
            info += f"📄 <b>Описание:</b> {utils.escape_html(user.about[:200])}\n"
        
        return info

    def estimate_registration_date(self, user_id):
        """Приблизительная оценка даты регистрации по ID"""
        try:
            # Приблизительные данные на основе роста ID в Telegram
            # Это грубая оценка, не точная дата
            if user_id < 10000:
                return "2013-2014 (ранний пользователь)"
            elif user_id < 100000:
                return "2014-2015"
            elif user_id < 1000000:
                return "2015-2016"
            elif user_id < 10000000:
                return "2016-2017"
            elif user_id < 100000000:
                return "2017-2018"
            elif user_id < 500000000:
                return "2018-2019"
            elif user_id < 1000000000:
                return "2019-2020"
            elif user_id < 2000000000:
                return "2020-2021"
            elif user_id < 3000000000:
                return "2021-2022"
            elif user_id < 4000000000:
                return "2022-2023"
            elif user_id < 5000000000:
                return "2023-2024"
            else:
                return "2024-настоящее время"
        except:
            return self.strings["unknown"]

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

    def get_user_info_from_message(self, message, reply=None):
        """Получает информацию о пользователе из сообщения"""
        if reply and reply.sender:
            return reply.sender
        elif message.sender:
            return message.sender
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
            await utils.answer(message, "⚠️ <b>Поиск пользователя по ID/username пока не поддерживается.</b>\n💡 <b>Используйте команду в ответ на сообщение пользователя</b>")
            return
        # Если нет реплая, используем отправителя текущего сообщения
        elif message.sender:
            user_entity = message.sender
        else:
            await utils.answer(
                message, 
                self.strings["invalid_args"].format(
                    self.get_prefix(), 
                    self.get_prefix()
                )
            )
            return
        
        if not user_entity:
            await utils.answer(message, self.strings["user_not_found"])
            return
        
        # Показываем процесс
        await utils.answer(message, self.strings["processing"])
        
        try:
            # Форматируем информацию
            info_text = self.format_user_info(user_entity, None)
            
            # Отправляем информацию
            await utils.answer(message, info_text)
                
        except Exception as e:
            await utils.answer(message, self.strings["error"].format(str(e)))