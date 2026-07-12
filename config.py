"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> frozenset[int]:
    return frozenset(int(chunk) for chunk in raw.split(",") if chunk.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]
    database_url: str
    log_level: str
    support_contact: str
    base_dir: str = field(default_factory=lambda: os.path.dirname(os.path.abspath(__file__)))

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids

    @classmethod
    def load(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

        return cls(
            bot_token=bot_token,
            admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/shopbot.db"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            support_contact=os.getenv("SUPPORT_CONTACT", "@YourSupportUsername"),
        )


settings = Settings.load()
