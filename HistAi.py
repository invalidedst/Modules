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
from typing import List, Optional

@loader.tds
class HistAI(loader.Module):
    """кидает что было пока ты отходил по дрочить  
    📄 Гайд: https://telegra.ph/NE-TUTOR-07-17"""
    strings = {
        "name": "HistAI",
        "cfg_key": "Ключ Gemini",
        "cfg_limit": "Сколько сообщений брать",
        "cfg_mode": "Режим: agro / norm",
        "no_key": "<emoji document_id=5312526098750252863>🚫</emoji> <b>Ключ Gemini не задан</b>",
        "processing": "<emoji document_id=5326015457155770266>⏳</emoji> <b>Ща чекну…</b>",
        "done_all": "<emoji document_id=5328311576736833844>🤖</emoji> <b>Пока ты дрочил, в чате было такое:</b>\n\n<blockquote expandable>{txt}</blockquote>",
        "done_user": "<emoji document_id=5328311576736833844>🤖</emoji> <b>Пока ты дрочил, {nick} написал:</b>\n\n<blockquote expandable>{txt}</blockquote>",
        "no_target": "<b>Кого чекать? Укажи @username или реплай.</b>",
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

    def _prep_all(self, msgs: List[Message]) -> str:
        lines = []
        for msg in reversed(msgs):
            if msg.sender and str(getattr(msg.sender, "username", "") or "").endswith("_bot"):
                continue
            nick = str(getattr(msg.sender, "username", "") or getattr(msg.sender, "first_name", "") or getattr(msg.sender, "id", "Unknown"))
            ts = msg.date.strftime("%H:%M")

            if msg.sticker:
                content = "[стикер]"
            elif msg.gif:
                content = "[гиф]"
            elif msg.photo:
                content = "[фото]"
            elif msg.video:
                content = "[видео]"
            elif msg.video_note:
                content = "[кружок]"
            elif msg.voice:
                content = "[голос]"
            elif msg.audio:
                content = "[аудио]"
            elif msg.document:
                content = "[файл]"
            else:
                content = (msg.raw_text or "").strip()

            lines.append(f"[{ts}] {nick}: {content}")
        return "\n".join(lines)

    def _prep_user(self, msgs: List[Message], user_id: int, user_name: str) -> str:
        lines = []
        for msg in reversed(msgs):
            if msg.sender_id != user_id:
                continue
            ts = msg.date.strftime("%H:%M")

            if msg.sticker:
                content = "[стикер]"
            elif msg.gif:
                content = "[гиф]"
            elif msg.photo:
                content = "[фото]"
            elif msg.video:
                content = "[видео]"
            elif msg.video_note:
                content = "[кружок]"
            elif msg.voice:
                content = "[голос]"
            elif msg.audio:
                content = "[аудио]"
            elif msg.document:
                content = "[файл]"
            else:
                content = (msg.raw_text or "").strip()

            lines.append(f"[{ts}] {content}")
        return "\n".join(lines)

    @loader.command(
        ru_doc="Показать всё, что происходило пока ты отошёл. Можно указать @username или реплай.",
        en_doc="Show what happened while you were away. Use @username or reply to filter.",
        de_doc="Zeige, was passierte, während du weg warst. Nutze @username oder Antwort.",
    )
    async def ch(self, message: Message):
        """.ch (@username / reply) — конкретный юзер  
        .ch — вся история"""
        if not self.config["gemini_key"]:
            await utils.answer(message, self.strings["no_key"])
            return

        chat_id = utils.get_chat_id(message)
        msgs = [m async for m in self.client.iter_messages(chat_id, limit=self.config["history_limit"])]
        if not msgs:
            await utils.answer(message, "<b>Сообщений нет.</b>")
            return

        await message.delete()
        user_id: Optional[int] = None
        user_name: str = ""
        reply = await message.get_reply_message()

        if reply and reply.sender:
            user_id = reply.sender_id
            user_name = reply.sender.username or reply.sender.first_name or str(reply.sender.id)
        else:
            args = utils.get_args_raw(message).strip()
            if args.startswith("@"):
                username = args[1:]
                try:
                    ent = await self.client.get_entity(username)
                    user_id = ent.id
                    user_name = username
                except Exception:
                    user_id = None
            elif args.isdigit():
                user_id = int(args)
                try:
                    ent = await self.client.get_entity(user_id)
                    user_name = ent.username or ent.first_name or str(user_id)
                except Exception:
                    user_id = None

        if user_id is None:
            text = self._prep_all(msgs)
            if not text:
                await message.respond("<b>Ничего не найдено.</b>")
                return
            prompt = (
                "Составь подробный нумерованный список (1.-10.) из 10 пунктов, "
                "описывающих, что делали/обсуждали участники. "
                "Выводи ник без символа @. "
                f"{'Можно материться.' if self.config['mode'] == 'agro' else 'Без мата.'} "
                "Не добавляй вводных фраз."
            )
            res = await self._ask(prompt, text)
            out_str = self.strings["done_all"].format(txt=res)
        else:
            text = self._prep_user(msgs, user_id, user_name)
            if not text:
                await message.respond("<b>Ничего не найдено.</b>")
                return
            prompt = (
                "Составь подробный нумерованный список (1.-10.) из 10 пунктов, "
                "описывающих, что делал/писал этот участник. "
                "Выводи ник без символа @. "
                f"{'Можно материться.' if self.config['mode'] == 'agro' else 'Без мата.'} "
                "Не добавляй вводных фраз."
            )
            res = await self._ask(prompt, text)
            out_str = self.strings["done_user"].format(nick=user_name, txt=res)

        await self.client.send_message(
            entity=message.chat_id,
            message=out_str,
            reply_to=message.reply_to_msg_id or message.id
        )
