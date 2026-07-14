"""Admin-editable bot text settings (welcome message, etc.)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.setting_repository import SettingRepository

WELCOME_TEXT_KEY = "welcome_text"
DEFAULT_WELCOME_TEXT = (
    "Welcome to the Shop, {name}!\n\n"
    "Use the menu below to browse products, manage your balance, and more."
)


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = SettingRepository(session)

    async def get_welcome_text(self) -> str:
        value = await self.settings.get(WELCOME_TEXT_KEY)
        return value if value is not None else DEFAULT_WELCOME_TEXT

    async def set_welcome_text(self, text: str) -> None:
        await self.settings.set(WELCOME_TEXT_KEY, text)
        await self.session.commit()
