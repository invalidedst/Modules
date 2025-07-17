#  _____                          
# |_   _|____  ____ _ _ __   ___  
#   | |/ _ \ \/ / _` | '_ \ / _ \ 
#   | | (_) >  < (_| | | | | (_) |
#   |_|\___/_/\_\__,_|_| |_|\___/ 
#                             
# meta developer: @Toxano_Modules
# scope: @Toxano_Modules

from herokutl.types import Message
from .. import loader, utils
import asyncio
import google.generativeai as genai
from typing import List


@loader.tds
class HistAI(loader.Module):
    """кидает что было пока ты отходил по дрочить  
    📄 Гайд: [NE TUTOR](https://telegra.ph/NE-TUTOR-07-17)"""
    strings = {
        "name": "HistAI",
        "cfg_key": "Ключ Gemini",
        "cfg_limit": "Сколько сообщений брать",
        "cfg_mode": "Режим: agro / norm",
        "no_key": "<emoji document_id=5312526098750252863>🚫</emoji> <b>Ключ Gemini не задан</b>",
        "processing": "<emoji document_id=5326015457155770266>⏳</emoji> <b>Ща чекну…</b>",
        "done": "<emoji document_id=5328311576736833844>🤖</emoji> <b>AI проанализировал последние {cnt} сообщений:</b>\n\n<blockquote expandable>{txt}</blockquote>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("gemini_key", "", self.strings["cfg_key"], validator=loader.validators.Hidden()),
            loader.ConfigValue("history_limit", 250, self.strings["cfg_limit"], validator=loader.validators.Integer()),
            loader.ConfigValue("mode", "norm", self.strings["cfg_mode"], validator=loader.validators.Choice(["norm", "agro"])),
        )

    async def client_ready(self, client, db):
        if self.config["gemini_key"]:
            genai.configure(api_key=self.config["gemini_key"])

    async def _ask(self, prompt: str, text: str) -> str:
        try:
            return (await asyncio.to_thread(
                genai.GenerativeModel("gemini-2.0-flash").generate_content,
                prompt + "\n\n" + text
            )).text.strip()
        except Exception as e:
            return f"Ошибка Gemini: {e}"

    async def _prep(self, msgs: List[Message]) -> str:
        lines = []
        for msg in reversed(msgs):
            txt = (msg.raw_text or "").strip()
            if not txt:
                continue
            sender = msg.sender
            if not sender:
                nick = "Unknown"
            else:
                username = getattr(sender, "username", None) or ""
                if username.endswith("_bot"):
                    continue
                nick = username if username else str(sender.first_name or sender.id or "Unknown")
            ts = msg.date.strftime("%H:%M")
            lines.append(f"[{ts}] {nick}: {txt}")
        return "\n".join(lines)

    @loader.command()
    async def ch(self, message: Message):
        """Анализ последних сообщений чата"""
        if not self.config["gemini_key"]:
            await utils.answer(message, self.strings["no_key"])
            return

        await message.delete()  # убираем "Ща чекну…"
        chat_id = utils.get_chat_id(message)
        msgs = [m async for m in self.client.iter_messages(chat_id, limit=self.config["history_limit"])]
        if not msgs:
            await message.respond("<b>Сообщений нет.</b>")
            return

        text = await self._prep(msgs)
        mode = self.config["mode"]

        prompt = (
            "Составь подробный нумерованный список (1.-10.) из 10 пунктов, "
            "описывающих, что делали/обсуждали участники. "
            "Добавь небольшие детали, но не перегружай. "
            "Используй ники или юзернеймы без символа @. "
            f"{'Можно материться.' if mode == 'agro' else 'Без мата.'} "
            "Не добавляй вводных фраз."
        )
        res = await self._ask(prompt, text)

        try:
            await message.respond(self.strings["done"].format(cnt=len(msgs), txt=res))
        except Exception as e:
            if "TOPIC_CLOSED" in str(e):
                await message.respond(
                    "<emoji document_id=5312526098750252863>🚫</emoji> <b>Не могу отправить в закрытую/форум-ветку. "
                    "Вызови команду в обычном чате или открой тему.</b>"
                )
            else:
                await message.respond(f"<b>Ошибка отправки: {e}</b>")
