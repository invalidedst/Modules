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
    """Создание красивых изображений кода"""

    strings = {
        "name": "CodeImage",
        "processing": "🎨 Создаю изображение...",
        "no_reply": "❌ Ответь на сообщение с файлом",
        "no_file": "❌ Файл не найден",
        "file_too_large": "❌ Файл слишком большой (макс 50KB)",
        "api_error": "❌ Ошибка: {}",
        "unsupported_ext": "❌ Неподдерживаемый формат файла"
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "theme", 
                "dracula", 
                "Тема оформления",
                validator=loader.validators.Choice([
                    "dracula", "vsc-dark-plus", "material-dark", "nord", 
                    "darcula", "atom-dark", "synthwave84", "hopscotch"
                ])
            ),
            loader.ConfigValue(
                "line_numbers",
                True,
                "Номера строк",
                validator=loader.validators.Boolean()
            ),
            loader.ConfigValue(
                "scale",
                2,
                "Масштаб (1-5)",
                validator=loader.validators.Integer(minimum=1, maximum=5)
            )
        )

        self.ext_to_lang = {
            '.py': 'python', '.js': 'javascript', '.jsx': 'jsx', '.ts': 'typescript',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.php': 'php', '.go': 'go',
            '.rs': 'rust', '.html': 'html', '.css': 'css', '.json': 'json',
            '.xml': 'xml', '.yml': 'yaml', '.yaml': 'yaml', '.sh': 'bash',
            '.sql': 'sql', '.md': 'markdown', '.txt': 'text'
        }

        self.api_url = "https://code2img.vercel.app/api/to-image"

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

    def detect_language(self, filename):
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        return self.ext_to_lang.get(ext, 'text')

    async def generate_image(self, code, language):
        params = {
            'theme': self.config["theme"],
            'language': language,
            'line-numbers': str(self.config["line_numbers"]).lower(),
            'scale': str(self.config["scale"]),
            'show-background': 'true',
            'padding': '5'
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

    @loader.command()
    async def codeimg(self, message: Message):
        reply = await message.get_reply_message()
        
        if not reply:
            await utils.answer(message, self.strings["no_reply"])
            return
        
        if not reply.media:
            await utils.answer(message, self.strings["no_file"])
            return
        
        await utils.answer(message, self.strings["processing"])
        
        try:
            file_bytes = await self._client.download_media(reply.media, bytes)
            
            if len(file_bytes) > 50 * 1024:
                await utils.answer(message, self.strings["file_too_large"])
                return
            
            filename = getattr(reply.media, 'document', None)
            if filename and hasattr(filename, 'attributes'):
                for attr in filename.attributes:
                    if hasattr(attr, 'file_name'):
                        filename = attr.file_name
                        break
            else:
                filename = "code.txt"
            
            try:
                code_content = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    code_content = file_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    await utils.answer(message, "❌ Не удалось декодировать файл")
                    return
            
            language = self.detect_language(filename)
            
            if language == 'text':
                await utils.answer(message, self.strings["unsupported_ext"])
                return
            
            image_bytes = await self.generate_image(code_content, language)
            
            await self._client.send_file(
                message.peer_id,
                io.BytesIO(image_bytes),
                mime_type="image/jpeg",
                reply_to=message.reply_to_msg_id
            )
            
            await message.delete()
            
        except Exception as e:
            await utils.answer(message, self.strings["api_error"].format(str(e)))