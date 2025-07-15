#  _____                          
# |_   _|____  ____ _ _ __   ___  
#   | |/ _ \ \/ / _` | '_ \ / _ \ 
#   | | (_) >  < (_| | | | | (_) |
#   |_|\___/_/\_\__,_|_| |_|\___/ 
#                              
# meta banner: https://i.ibb.co/3yNfKRLL/image-10490.jpg
# meta developer: @toxano_modules 
# scope: @toxano_modules

import aiohttp
import asyncio
import io
from herokutl.types import Message
from .. import loader, utils

@loader.tds
class CodeImageMod(loader.Module):
    """Модуль для создания красивых изображений кода"""

    strings = {
        "name": "CodeImage",
        "processing": "🎨 <b>Создаю изображение кода...</b>",
        "no_reply": "❌ <b>Ответьте на сообщение с файлом кода!</b>",
        "no_file": "❌ <b>В сообщении нет файла!</b>",
        "file_too_large": "❌ <b>Файл слишком большой! Максимальный размер: 50KB</b>",
        "api_error": "❌ <b>Ошибка API:</b> <code>{}</code>",
        "unsupported_ext": "❌ <b>Неподдерживаемое расширение файла!</b>\n💡 <b>Поддерживаются:</b> <code>{}</code>",
        "download_error": "❌ <b>Ошибка загрузки файла!</b>",
        "success": "✅ <b>Изображение создано!</b>",
        "settings": "⚙️ <b>Настройки CodeImage:</b>\n\n🎨 <b>Тема:</b> <code>{}</code>\n📝 <b>Язык:</b> <code>{}</code>\n🔢 <b>Номера строк:</b> <code>{}</code>\n📐 <b>Масштаб:</b> <code>{}</code>\n🖼️ <b>Фон:</b> <code>{}</code>\n📏 <b>Отступы:</b> <code>{}</code>",
        "theme_list": "🎨 <b>Доступные темы:</b>\n\n<code>{}</code>",
        "lang_list": "📝 <b>Поддерживаемые языки:</b>\n\n<code>{}</code>"
    }

    strings_ru = {
        "processing": "🎨 <b>Создаю изображение кода...</b>",
        "no_reply": "❌ <b>Ответьте на сообщение с файлом кода!</b>",
        "no_file": "❌ <b>В сообщении нет файла!</b>",
        "file_too_large": "❌ <b>Файл слишком большой! Максимальный размер: 50KB</b>",
        "api_error": "❌ <b>Ошибка API:</b> <code>{}</code>",
        "unsupported_ext": "❌ <b>Неподдерживаемое расширение файла!</b>\n💡 <b>Поддерживаются:</b> <code>{}</code>",
        "download_error": "❌ <b>Ошибка загрузки файла!</b>",
        "success": "✅ <b>Изображение создано!</b>",
        "settings": "⚙️ <b>Настройки CodeImage:</b>\n\n🎨 <b>Тема:</b> <code>{}</code>\n📝 <b>Язык:</b> <code>{}</code>\n🔢 <b>Номера строк:</b> <code>{}</code>\n📐 <b>Масштаб:</b> <code>{}</code>\n🖼️ <b>Фон:</b> <code>{}</code>\n📏 <b>Отступы:</b> <code>{}</code>",
        "theme_list": "🎨 <b>Доступные темы:</b>\n\n<code>{}</code>",
        "lang_list": "📝 <b>Поддерживаемые языки:</b>\n\n<code>{}</code>"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "theme", 
                "dracula", 
                "Тема для подсветки кода",
                validator=loader.validators.Choice([
                    "a11y-dark", "atom-dark", "base16-ateliersulphurpool.light", "cb", 
                    "darcula", "default", "dracula", "duotone-dark", "duotone-earth", 
                    "duotone-forest", "duotone-light", "duotone-sea", "duotone-space", 
                    "ghcolors", "hopscotch", "material-dark", "material-light", 
                    "material-oceanic", "nord", "pojoaque", "shades-of-purple", 
                    "synthwave84", "vs", "vsc-dark-plus", "xonokai"
                ])
            ),
            loader.ConfigValue(
                "language",
                "auto",
                "Язык программирования (auto = автоопределение)",
                validator=loader.validators.Choice([
                    "auto", "c", "css", "cpp", "go", "html", "java", "javascript", 
                    "jsx", "php", "python", "rust", "typescript", "json", "xml", 
                    "yaml", "bash", "sql", "markdown", "dockerfile"
                ])
            ),
            loader.ConfigValue(
                "line_numbers",
                True,
                "Показывать номера строк",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "scale",
                2,
                "Масштаб изображения (1-5)",
                validator=loader.validators.Integer(minimum=1, maximum=5)
            ),
            loader.ConfigValue(
                "background",
                True,
                "Показывать фон",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "padding",
                5,
                "Отступы (0-15)",
                validator=loader.validators.Integer(minimum=0, maximum=15)
            ),
            loader.ConfigValue(
                "background_color",
                "#282a36",
                "Цвет фона (CSS формат)",
                validator=loader.validators.String()
            )
        )

        # Соответствие расширений файлов языкам программирования
        self.ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'jsx',
            '.ts': 'typescript',
            '.tsx': 'jsx',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.sh': 'bash',
            '.sql': 'sql',
            '.md': 'markdown',
            '.dockerfile': 'dockerfile',
            '.txt': 'text'
        }

        # API endpoint
        self.api_url = "https://code2img.vercel.app/api/to-image"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    def detect_language(self, filename, content):
        """Определяет язык программирования по расширению файла"""
        if self.config["language"] != "auto":
            return self.config["language"]
        
        # Получаем расширение файла
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Возвращаем соответствующий язык или 'text' по умолчанию
        return self.ext_to_lang.get(ext, 'text')

    async def generate_image(self, code, language):
        """Генерирует изображение кода через API"""
        try:
            params = {
                'theme': self.config["theme"],
                'language': language,
                'line-numbers': str(self.config["line_numbers"]).lower(),
                'scale': str(self.config["scale"]),
                'show-background': str(self.config["background"]).lower(),
                'padding': str(self.config["padding"]),
                'background-color': self.config["background_color"]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    data=code,
                    params=params,
                    headers={'Content-Type': 'text/plain'}
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"Ошибка генерации изображения: {str(e)}")

    @loader.command(
        ru_doc="Создать изображение кода из файла"
    )
    async def codeimg(self, message: Message):
        """Создать изображение кода из файла"""
        reply = await message.get_reply_message()
        
        if not reply:
            await utils.answer(message, self.strings["no_reply"])
            return
        
        if not reply.media:
            await utils.answer(message, self.strings["no_file"])
            return
        
        # Показываем процесс
        await utils.answer(message, self.strings["processing"])
        
        try:
            # Скачиваем файл
            file_bytes = await self._client.download_media(reply.media, bytes)
            
            # Проверяем размер файла (максимум 50KB)
            if len(file_bytes) > 50 * 1024:
                await utils.answer(message, self.strings["file_too_large"])
                return
            
            # Получаем имя файла
            filename = getattr(reply.media, 'document', None)
            if filename and hasattr(filename, 'attributes'):
                for attr in filename.attributes:
                    if hasattr(attr, 'file_name'):
                        filename = attr.file_name
                        break
            else:
                filename = "code.txt"
            
            # Декодируем содержимое файла
            try:
                code_content = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    code_content = file_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    await utils.answer(message, "❌ <b>Не удалось декодировать файл!</b>")
                    return
            
            # Определяем язык
            language = self.detect_language(filename, code_content)
            
            # Проверяем поддержку расширения
            if language == 'text' and self.config["language"] == "auto":
                supported_exts = ', '.join(self.ext_to_lang.keys())
                await utils.answer(message, self.strings["unsupported_ext"].format(supported_exts))
                return
            
            # Генерируем изображение
            image_bytes = await self.generate_image(code_content, language)
            
            # Создаем caption
            caption = f"🎨 <b>Код:</b> <code>{filename}</code>\n📝 <b>Язык:</b> <code>{language}</code>\n🎭 <b>Тема:</b> <code>{self.config['theme']}</code>"
            
            # Отправляем изображение
            await self._client.send_file(
                message.peer_id,
                io.BytesIO(image_bytes),
                caption=caption,
                parse_mode='html',
                reply_to=message.reply_to_msg_id
            )
            
            # Удаляем сообщение с процессом
            await message.delete()
            
        except Exception as e:
            await utils.answer(message, self.strings["api_error"].format(str(e)))

    @loader.command(
        ru_doc="Показать настройки модуля"
    )
    async def codeimgcfg(self, message: Message):
        """Показать настройки модуля"""
        settings_text = self.strings["settings"].format(
            self.config["theme"],
            self.config["language"],
            "Да" if self.config["line_numbers"] else "Нет",
            f"{self.config['scale']}x",
            "Да" if self.config["background"] else "Нет",
            self.config["padding"]
        )
        
        await utils.answer(message, settings_text)

    @loader.command(
        ru_doc="Показать список доступных тем"
    )
    async def codeimgthemes(self, message: Message):
        """Показать список доступных тем"""
        themes = [
            "a11y-dark", "atom-dark", "base16-ateliersulphurpool.light", "cb",
            "darcula", "default", "dracula", "duotone-dark", "duotone-earth",
            "duotone-forest", "duotone-light", "duotone-sea", "duotone-space",
            "ghcolors", "hopscotch", "material-dark", "material-light",
            "material-oceanic", "nord", "pojoaque", "shades-of-purple",
            "synthwave84", "vs", "vsc-dark-plus", "xonokai"
        ]
        
        themes_text = '\n'.join([f"• {theme}" for theme in themes])
        await utils.answer(message, self.strings["theme_list"].format(themes_text))

    @loader.command(
        ru_doc="Показать список поддерживаемых языков"
    )
    async def codeimglangs(self, message: Message):
        """Показать список поддерживаемых языков"""
        langs = [
            "auto (автоопределение)", "c", "css", "cpp", "go", "html", "java",
            "javascript", "jsx", "php", "python", "rust", "typescript", "json",
            "xml", "yaml", "bash", "sql", "markdown", "dockerfile"
        ]
        
        langs_text = '\n'.join([f"• {lang}" for lang in langs])
        await utils.answer(message, self.strings["lang_list"].format(langs_text))