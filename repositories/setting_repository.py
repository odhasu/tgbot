"""Data access for Setting key/value records."""

from __future__ import annotations

from models.setting import Setting
from repositories.base import BaseRepository


class SettingRepository(BaseRepository):
    async def get(self, key: str) -> str | None:
        setting = await self.session.get(Setting, key)
        return setting.value if setting else None

    async def set(self, key: str, value: str) -> Setting:
        setting = await self.session.get(Setting, key)
        if setting is None:
            setting = Setting(key=key, value=value)
            self.session.add(setting)
        else:
            setting.value = value
        await self.session.flush()
        return setting
