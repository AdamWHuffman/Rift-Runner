import asyncio
from pathlib import Path

import yaml
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.goal import Goal
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


async def seed_goals() -> int:
    entries = yaml.safe_load((CONFIG_DIR / "goals.yaml").read_text())
    async with async_session_factory() as db:
        for entry in entries:
            existing = await db.scalar(select(Goal).where(Goal.key == entry["key"]))
            fields = dict(
                display_name=entry["display_name"],
                description=entry["description"].strip(),
                zone_weight_targets=entry["zone_weight_targets"],
                multiplier_min=entry["multiplier_min"],
                multiplier_max=entry["multiplier_max"],
            )
            if existing is None:
                db.add(Goal(key=entry["key"], **fields))
            else:
                for field, value in fields.items():
                    setattr(existing, field, value)
        await db.commit()
    return len(entries)


async def main() -> None:
    skill_count = await seed_skills()
    print(f"Seeded {skill_count} skills.")
    goal_count = await seed_goals()
    print(f"Seeded {goal_count} goals.")


if __name__ == "__main__":
    asyncio.run(main())
