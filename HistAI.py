#  _____
# |_   _|____  ____ _ _ __   ___
#   | |/ _ \ \/ / _` | '_ \ / _ \
#   | | (_) >  < (_| | | | | (_) |
#   |_|\___/_/\_\__,_|_| |_|\___/
#
# meta developer: @Toxano_Modules
# scope: @Toxano_Modules

from telethon.tl.custom import Button
from telethon.types import Message
from .. import loader, utils
import asyncio
import google.generativeai as genai
from typing import List, Optional
import os
import re

CHUNK_SEP = "\n"
MAX_PAGE = 3900
CB_PREFIX = "histai_"
HARD_LIMIT = 180          
MAX_LINE_LEN = 120         

@loader.tds
class HistAI(loader.Module):
    """кидает что было пока ты отходил"""

    strings = {
        "name": "HistAI",
        "cfg_key": "Ключ Gemini",
        "cfg_limit": "Сколько сообщений брать",
        "cfg_mode": "Режим: norm / agro / neko",
        "no_key": "<emoji document_id=5312526098750252863>🚫</emoji> <b>Ключ Gemini не задан</b>",
        "processing": "<emoji document_id=5326015457155770266>⏳</emoji> <b>Ща чекну…</b>",
        "done_all": "<emoji document_id=5328311576736833844>🤖</emoji> <b>AI проанализировал последние {limit} сообщений.\nВот что вы пропустили:</b>",
        "done_user": "<emoji document_id=5328311576736833844>🤖</emoji> <b>AI проанализировал последние {limit} сообщений от {nick}.\nВот что вы пропустили:</b>",
        "no_target": "<b>Кого чекать? Укажи @username или реплай.</b>",
        "page": "📄 {cur}/{total}",
        "blocked": "<emoji document_id=5312526098750252863>🚫</emoji> <b>Gemini отказался анализировать чат (слишком много мата/оскорблений). Вот краткая сводка без ИИ:</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue("gemini_key", "", self.strings["cfg_key"], validator=loader.validators.Hidden()),
            loader.ConfigValue("history_limit", 150, self.strings["cfg_limit"], validator=loader.validators.Integer(minimum=1, maximum=HARD_LIMIT)),
            loader.ConfigValue("mode", "norm", self.strings["cfg_mode"], validator=loader.validators.Choice(["norm", "agro", "neko"])),
        )
        self._db = {}

    async def client_ready(self, client, db):
        self.client = client

    async def _ask(self, prompt: str, text: str) -> str:
        key = self.config["gemini_key"].strip() or os.getenv("GOOGLE_API_KEY")
        if not key:
            return "❌ Ни API-key в конфиге, ни переменная GOOGLE_API_KEY не заданы."
        try:
            genai.configure(api_key=key)
            response = await asyncio.to_thread(
                genai.GenerativeModel("gemini-1.5-flash").generate_content,
                prompt + "\n\n" + text,
                safety_settings={
                    "HARASSMENT": "BLOCK_NONE",
                    "HATE_SPEECH": "BLOCK_NONE",
                    "SEXUAL": "BLOCK_NONE",
                    "DANGEROUS": "BLOCK_NONE",
                }
            )
            if not response.candidates:
                return "BLOCKED"
            return response.text.strip()
        except Exception as e:
            return f"Ошибка Gemini: {e}"

    def _clean(self, txt: str) -> str:
        if not txt:
            return ""
        txt = re.sub(r"http\S+", "<ссылка>", txt)           # убираем ссылки
        txt = re.sub(r"[а-яё]*[хx]+[уy]+[йiюяеё]\w*", "[мат]", txt, flags=re.I)
        return txt[:MAX_LINE_LEN]

    def _media(self, m: Message) -> str:
        for t in ("sticker", "gif", "photo", "video", "voice", "audio", "document"):
            if getattr(m, t, None):
                return f"[{t}]"
        return ""

    def _prep_all(self, msgs: List[Message]) -> str:
        lines = []
        for m in reversed(msgs[-HARD_LIMIT:]):
            if not m.sender:
                continue
            if (getattr(m.sender, "username") or "").endswith("_bot"):
                continue
            nick = f"{m.sender.first_name or 'Без_имени'} ({m.sender.id})"
            time = m.date.strftime("%H:%M")
            body = self._clean(m.raw_text) or self._media(m)
            if m.is_reply:
                body = "→ " + body
            lines.append(f"[{time}] {nick} > {body}")
        return "\n".join(lines)

    def _prep_user(self, msgs: List[Message], uid: int) -> str:
        lines = []
        for m in reversed(msgs[-HARD_LIMIT:]):
            if m.sender_id != uid:
                continue
            time = m.date.strftime("%H:%M")
            body = self._clean(m.raw_text) or self._media(m)
            if m.is_reply:
                body = "→ " + body
            lines.append(f"[{time}] {body}")
        return "\n".join(lines)

    def _paginate(self, text: str) -> List[str]:
        pages, buf = [""], ""
        for ln in text.splitlines():
            if len(buf + ln) + 1 > MAX_PAGE:
                pages.append(ln)
                buf = ln
            else:
                buf += (("\n" + ln) if buf else ln)
                pages[-1] = buf
        return pages or [""]

    async def _send_page(self, cid: int, pages: List[str], idx: int, hdr: str, rpl: int):
        kb = []
        if len(pages) > 1:
            row = []
            if idx:
                row.append(Button.inline("⬅️", f"{CB_PREFIX}{idx-1}"))
            row.append(Button.inline(self.strings["page"].format(cur=idx+1, total=len(pages)), "noop"))
            if idx < len(pages) - 1:
                row.append(Button.inline("➡️", f"{CB_PREFIX}{idx+1}"))
            kb = [row]
        await self.client.send_message(
            entity=cid,
            message=f"{hdr}\n\n<blockquote expandable>{pages[idx]}</blockquote>",
            buttons=kb or None,
            reply_to=rpl
        )

    @loader.command(
        ru_doc="Показать всё, что происходило пока ты отошёл. Можно указать @username или реплай.",
        en_doc="Show what happened while you were away. Use @username or reply to filter.",
    )
    async def ch(self, message: Message):
        if not self.config["gemini_key"] and not os.getenv("GOOGLE_API_KEY"):
            await utils.answer(message, self.strings["no_key"])
            return

        cid = utils.get_chat_id(message)
        limit = min(self.config["history_limit"], HARD_LIMIT)

        msgs = [m async for m in self.client.iter_messages(cid, limit=limit + 50)]
        msgs = [m for m in msgs if not (getattr(m.sender, "username") or "").endswith("_bot")][:limit]

        if not msgs:
            await utils.answer(message, "<b>Сообщений нет.</b>")
            return

        await message.delete()

        user_id, user_name = None, ""
        if reply := await message.get_reply_message():
            user_id, user_name = reply.sender_id, (reply.sender.first_name or str(reply.sender.id))
        else:
            arg = utils.get_args_raw(message).strip()
            if arg.startswith("@"):
                try:
                    ent = await self.client.get_entity(arg[1:])
                    user_id, user_name = ent.id, (ent.first_name or str(ent.id))
                except Exception:
                    user_id = None
            elif arg.isdigit():
                try:
                    ent = await self.client.get_entity(int(arg))
                    user_id, user_name = ent.id, (ent.first_name or str(ent.id))
                except Exception:
                    user_id = None

        owner = (await self.client.get_me()).first_name or "Хозяин"

        if user_id is None:
            raw_text = self._prep_all(msgs)
            header = self.strings["done_all"].format(limit=len(msgs))
            prompt = (
                f"Ниже список сообщений из Telegram-чата строго в хронологическом порядке.\n"
                f"Каждая строка имеет формат:\n[время] имя (id) > текст или [тип медиа]\n\n"
                f"Твоя задача — максимально точно пересказать только то, что действительно написали люди.\n"
                f"- Не добавляй своих комментариев, не придумывай факты.\n"
                f"- Не объединяй разных людей в одно лицо.\n"
                f"- Используй формат: - [время] имя: краткий текст или [тип медиа]\n"
                f"{'Будь слегка саркастичным, но не фантазируй.' if self.config['mode'] == 'agro' else 'Без мата и без фантазий.'}"
            )
        else:
            raw_text = self._prep_user(msgs, user_id)
            header = self.strings["done_user"].format(limit=len(raw_text.splitlines()), nick=user_name)
            prompt = (
                f"Ниже все сообщения пользователя {user_name} (id{user_id}) из Telegram-чата.\n"
                f"Каждая строка имеет формат:\n[время] текст или [фото/файл/…]\n\n"
                f"Перечисли только то, что он действительно написал/отправил.\n"
                f"Не добавляй ничего от себя.\n"
                f"Формат: - [время] краткий текст или [тип медиа]\n"
                f"{'Будь слегка саркастичным, но не выдумывай.' if self.config['mode'] == 'agro' else 'Без мата и без фантазий.'}"
            )

        ai_text = await self._ask(prompt, raw_text)
        if ai_text == "BLOCKED":

            pages = self._paginate(raw_text)
            header = self.strings["blocked"]
        elif ai_text.startswith("Ошибка"):
            pages = [ai_text]
        else:
            pages = self._paginate(ai_text)

        self._db[f"hist:{cid}"] = pages if pages != [""] else None
        await self._send_page(cid, pages, 0, header, message.reply_to_msg_id or message.id)

    @loader.callback_handler()
    async def _flip_page(self, call):
        if not call.data.startswith(CB_PREFIX):
            return
        try:
            idx = int(call.data[len(CB_PREFIX):])
        except ValueError:
            await call.answer("Неверный индекс")
            return

        cid = call.message.chat_id
        pages = self._db.get(f"hist:{cid}")
        if not isinstance(pages, list) or not pages:
            await call.answer("Сводка устарела или пуста.")
            await call.message.delete()
            self._db.pop(f"hist:{cid}", None)
            return
        if idx < 0 or idx >= len(pages):
            await call.answer("Страница не найдена")
            return

        header = call.message.text.split("\n\n<blockquote expandable>")[0]
        await self._send_page(cid, pages, idx, header,
                              call.message.reply_to_msg_id or call.message.id)
        await call.message.delete()
