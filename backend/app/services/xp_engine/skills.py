"""Tier-2 registered-function skill orchestration.

Each skill needs real per-user historical context (rolling personal bests,
averages, streaks) that a simple declarative rule can't express cleanly, so
skills are a small registry of Python functions (skill_formulas.py) rather
than DB-driven rules. Adding a new skill later is one formula function + one
`skills` catalog row -- this orchestration loop never needs to change.

Reuses xp_engine.leveling verbatim, exactly as main leveling does, just with
each skill tracking its own independent SkillProgress row and EMA.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.skill import Skill
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.xp_engine import leveling, skill_formulas

FORMULA_VERSION = 1

SkillCalculator = Callable[[Activity, list[Activity]], float]

# Skills compared within the same activity type (pace/distance/HR only make
# sense relative to the same kind of effort) vs. across all types (the habit
# loop doesn't care whether it was a run or a walk).
SAME_TYPE_SKILLS = {"speed", "endurance", "health"}

SKILL_CALCULATORS: dict[str, SkillCalculator] = {
    "speed": skill_formulas.speed_skill_xp,
    "endurance": skill_formulas.endurance_skill_xp,
    "health": skill_formulas.health_skill_xp,
    "consistency": skill_formulas.consistency_skill_xp,
    "explorer": skill_formulas.explorer_skill_xp,
}


@dataclass
class SkillLevelUpEvent:
    skill_key: str
    from_level: int
    to_level: int


async def process_activity_skills(db: AsyncSession, user: User, activity: Activity) -> list[SkillLevelUpEvent]:
    """Compute and apply this activity's XP for every active, registered
    skill. Does not commit -- the caller controls the transaction boundary."""
    skills = (await db.scalars(select(Skill).where(Skill.is_active.is_(True)))).all()
    if not skills:
        return []

    same_type_history = list(
        await db.scalars(
            select(Activity).where(
                Activity.user_id == user.id,
                Activity.activity_type == activity.activity_type,
                Activity.id != activity.id,
            )
        )
    )
    all_type_history = list(
        await db.scalars(select(Activity).where(Activity.user_id == user.id, Activity.id != activity.id))
    )

    level_ups: list[SkillLevelUpEvent] = []

    for skill in skills:
        calculator = SKILL_CALCULATORS.get(skill.key)
        if calculator is None:
            continue

        history = same_type_history if skill.key in SAME_TYPE_SKILLS else all_type_history
        earned_xp = round(calculator(activity, history))
        if earned_xp <= 0:
            continue

        progress = await db.scalar(
            select(SkillProgress).where(SkillProgress.user_id == user.id, SkillProgress.skill_id == skill.id)
        )
        if progress is None:
            seed = leveling.initial_state()
            progress = SkillProgress(
                user_id=user.id,
                skill_id=skill.id,
                level=seed.level,
                xp_into_level=seed.xp_into_level,
                xp_to_next_level_snapshot=seed.xp_to_next_level_snapshot,
                activities_this_level=seed.activities_this_level,
                avg_xp_per_activity_ema=seed.avg_xp_per_activity_ema,
            )
            db.add(progress)

        state = leveling.LevelingState(
            level=progress.level,
            xp_into_level=progress.xp_into_level,
            xp_to_next_level_snapshot=progress.xp_to_next_level_snapshot,
            activities_this_level=progress.activities_this_level,
            avg_xp_per_activity_ema=progress.avg_xp_per_activity_ema,
        )
        result = leveling.apply_progress(state, earned_xp)
        level_before = progress.level

        progress.level = result.state.level
        progress.xp_into_level = result.state.xp_into_level
        progress.xp_to_next_level_snapshot = result.state.xp_to_next_level_snapshot
        progress.activities_this_level = result.state.activities_this_level
        progress.avg_xp_per_activity_ema = result.state.avg_xp_per_activity_ema

        db.add(
            XPTransaction(
                user_id=user.id,
                activity_id=activity.id,
                xp_type="skill",
                target_key=skill.key,
                base_xp=earned_xp,
                multipliers={},
                final_xp=earned_xp,
                formula_version=FORMULA_VERSION,
                level_before=level_before,
                level_after=result.state.level,
            )
        )

        level_ups.extend(
            SkillLevelUpEvent(skill_key=skill.key, from_level=e.from_level, to_level=e.to_level)
            for e in result.level_ups
        )

    return level_ups
