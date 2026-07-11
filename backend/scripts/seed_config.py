import asyncio
from pathlib import Path

import yaml
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.skill import Skill

CONFIG_DIR = Path(__file__).resolve().parent.parent / "app" / "config_data"


async def seed_skills() -> int:
    entries = yaml.safe_load((CONFIG_DIR / "skills.yaml").read_text())
    async with async_session_factory() as db:
        for entry in entries:
            existing = await db.scalar(select(Skill).where(Skill.key == entry["key"]))
            if existing is None:
                db.add(Skill(key=entry["key"], display_name=entry["display_name"]))
            else:
                existing.display_name = entry["display_name"]
        await db.commit()
    return len(entries)


async def main() -> None:
    count = await seed_skills()
    print(f"Seeded {count} skills.")


if __name__ == "__main__":
    asyncio.run(main())
