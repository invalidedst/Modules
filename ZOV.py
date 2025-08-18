# meta developer: @toxano_modules 

import asyncio
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class ZOVMod(loader.Module):
    """ZOV"""

    strings = {"name": "ZOV", "zov": "<b>ZOOOV</b>"}
    strings_ru = {"zov": "<b>ZOOOV</b>"}

    def __init__(self):
        self.config = loader.ModuleConfig()

    @loader.command(
        ru_doc="ZOV",
        en_doc="ZOV",
        alias="zov",
        category="ZOV"
    )
    async def zov(self, message: Message):
        """ZOV"""
        await utils.answer(message, self.strings["zov"])
