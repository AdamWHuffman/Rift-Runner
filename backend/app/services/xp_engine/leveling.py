"""The shared adaptive leveling primitive.

Reused verbatim for main leveling (Phase 3), skill leveling (Phase 4), and
course-mastery leveling (Phase 5) -- one leveling primitive, three consumers.

The hard requirement this satisfies: leveling should never take more than 10
activities, or fewer than 5, regardless of the user's fitness level -- while
still feeling like real, earned progress rather than a fixed grind. This
works by decoupling two things that are usually conflated:

  - HOW MANY activities a level takes: activities_to_next_level(level) is a
    pure function of the level number alone, hard-bounded to [5, 10]. True
    for every user, unrelated to how fit they are.
  - HOW MUCH XP that requires: anchored to a rolling EMA of this user's own
    recent XP-per-activity, so the absolute XP number grows naturally as the
    user's real fitness (and therefore typical XP yield) grows, without ever
    violating the activity-count guarantee.

The XP target for a level is frozen the moment that level is reached (a
"snapshot") so it never moves mid-level even if the EMA drifts -- and if a
user still hasn't hit that target by the Nth activity, the level-up fires
anyway. The 5-10 promise is structural, not statistical.
"""

from dataclasses import dataclass

EMA_ALPHA = 0.2
MIN_ACTIVITIES_PER_LEVEL = 5
MAX_ACTIVITIES_PER_LEVEL = 10
ACTIVITIES_PER_LEVEL_GROWTH_EVERY = 6

# Seed for a brand-new leveling track (main level, a new skill, a newly
# discovered course) before it has any real activity history of its own --
# roughly what a modest 20-30 min moderate effort should yield.
INITIAL_EMA_SEED = 80.0


def initial_state(level: int = 1, ema: float = INITIAL_EMA_SEED) -> "LevelingState":
    return LevelingState(
        level=level,
        xp_into_level=0.0,
        xp_to_next_level_snapshot=activities_to_next_level(level) * ema,
        activities_this_level=0,
        avg_xp_per_activity_ema=ema,
    )


def activities_to_next_level(level: int) -> int:
    """How many activities it takes to clear `level`. Pure function of level only."""
    return min(
        MAX_ACTIVITIES_PER_LEVEL,
        MIN_ACTIVITIES_PER_LEVEL + level // ACTIVITIES_PER_LEVEL_GROWTH_EVERY,
    )


def update_ema(previous_ema: float, latest_xp: float, alpha: float = EMA_ALPHA) -> float:
    return alpha * latest_xp + (1 - alpha) * previous_ema


@dataclass
class LevelingState:
    level: int
    xp_into_level: float
    xp_to_next_level_snapshot: float
    activities_this_level: int
    avg_xp_per_activity_ema: float


@dataclass
class LevelUpEvent:
    from_level: int
    to_level: int


@dataclass
class ProgressResult:
    state: LevelingState
    level_ups: list[LevelUpEvent]


def apply_progress(state: LevelingState, earned_xp: float) -> ProgressResult:
    """Apply one activity's XP to a leveling track.

    Returns the updated state and any level-up events. Usually just one --
    with the default EMA weighting, a single activity's own XP feeds into the
    same EMA that sizes the *next* level's target, so an outlier effort can't
    cascade through several levels at once (the target inflates right along
    with it). The loop still matters for resolving a pre-existing overflow in
    the incoming state (e.g. after a formula recalculation grants retroactive
    XP), where it can legitimately fast-forward through multiple levels.
    """
    ema = update_ema(state.avg_xp_per_activity_ema, earned_xp)
    xp_into_level = state.xp_into_level + earned_xp
    activities_this_level = state.activities_this_level + 1
    level = state.level
    target = state.xp_to_next_level_snapshot
    level_ups: list[LevelUpEvent] = []

    # The hard guarantee only forces the *first* level-up in this activity --
    # once triggered, any further cascading level-ups are earned normally by
    # having enough leftover XP to also clear the next level's target.
    force_level_up = activities_this_level >= activities_to_next_level(level)

    while xp_into_level >= target or force_level_up:
        new_level = level + 1
        level_ups.append(LevelUpEvent(from_level=level, to_level=new_level))
        xp_into_level = max(0.0, xp_into_level - target)
        level = new_level
        activities_this_level = 0
        target = activities_to_next_level(level) * ema
        force_level_up = False

    return ProgressResult(
        state=LevelingState(
            level=level,
            xp_into_level=xp_into_level,
            xp_to_next_level_snapshot=target,
            activities_this_level=activities_this_level,
            avg_xp_per_activity_ema=ema,
        ),
        level_ups=level_ups,
    )
