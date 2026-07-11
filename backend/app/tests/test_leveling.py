import random

import pytest

from app.services.xp_engine import leveling


def test_activities_to_next_level_matches_plan_examples() -> None:
    assert leveling.activities_to_next_level(1) == 5
    assert leveling.activities_to_next_level(6) == 6
    assert leveling.activities_to_next_level(12) == 7
    assert leveling.activities_to_next_level(18) == 8
    assert leveling.activities_to_next_level(24) == 9
    assert leveling.activities_to_next_level(30) == 10
    assert leveling.activities_to_next_level(36) == 10
    assert leveling.activities_to_next_level(1000) == 10


@pytest.mark.parametrize("level", range(1, 200))
def test_activities_to_next_level_always_within_bounds(level: int) -> None:
    assert 5 <= leveling.activities_to_next_level(level) <= 10


def test_ema_update_formula() -> None:
    assert leveling.update_ema(100.0, 200.0, alpha=0.2) == pytest.approx(120.0)
    assert leveling.update_ema(100.0, 100.0, alpha=0.2) == pytest.approx(100.0)


def _fresh_state(level: int = 1, ema: float = 80.0) -> leveling.LevelingState:
    return leveling.LevelingState(
        level=level,
        xp_into_level=0.0,
        xp_to_next_level_snapshot=leveling.activities_to_next_level(level) * ema,
        activities_this_level=0,
        avg_xp_per_activity_ema=ema,
    )


def test_apply_progress_no_level_up_when_below_target() -> None:
    state = _fresh_state()
    result = leveling.apply_progress(state, earned_xp=10.0)

    assert result.level_ups == []
    assert result.state.level == 1
    assert result.state.xp_into_level == pytest.approx(10.0)
    assert result.state.activities_this_level == 1


def test_apply_progress_levels_up_when_target_reached() -> None:
    state = _fresh_state(ema=100.0)  # target = 5 * 100 = 500
    result = leveling.apply_progress(state, earned_xp=500.0)

    assert len(result.level_ups) == 1
    assert result.level_ups[0].from_level == 1
    assert result.level_ups[0].to_level == 2
    assert result.state.level == 2
    assert result.state.activities_this_level == 0
    assert result.state.xp_into_level == pytest.approx(0.0)


def test_apply_progress_overflow_xp_carries_into_next_level() -> None:
    state = _fresh_state(ema=100.0)  # target = 500
    result = leveling.apply_progress(state, earned_xp=650.0)

    assert result.state.level == 2
    assert result.state.xp_into_level == pytest.approx(150.0)


def test_apply_progress_a_single_huge_activity_still_only_levels_up_once() -> None:
    """With alpha=0.2, a single activity's own XP can never cascade through
    multiple levels: the EMA it feeds into inflates the next level's target
    by exactly as much as the leftover overflow grows, so the two always
    stay out of reach of each other. This is expected, not a bug -- an
    outlier effort can't trivialize several levels at once."""
    state = _fresh_state(ema=50.0)  # target = 5 * 50 = 250
    result = leveling.apply_progress(state, earned_xp=5000.0)

    assert len(result.level_ups) == 1


def test_apply_progress_cascades_through_pre_existing_banked_overflow() -> None:
    """The loop still matters for state that already carries a large
    xp_into_level overflow -- e.g. after a formula recalculation retroactively
    grants XP. It must fast-forward through every level that XP covers,
    not just apply one level-up per call."""
    state = leveling.LevelingState(
        level=1,
        xp_into_level=9000.0,
        xp_to_next_level_snapshot=250.0,  # 5 * ema(50)
        activities_this_level=0,
        avg_xp_per_activity_ema=50.0,
    )
    result = leveling.apply_progress(state, earned_xp=1.0)

    assert len(result.level_ups) >= 2
    for i in range(len(result.level_ups) - 1):
        assert result.level_ups[i].to_level == result.level_ups[i + 1].from_level


def test_apply_progress_hard_guarantee_forces_level_up_on_nth_activity() -> None:
    """Even with zero XP earned, activities_to_next_level(1) == 5 activities
    must force a level-up on the 5th, per the structural guarantee."""
    state = _fresh_state(ema=1000.0)  # deliberately huge target, unreachable via XP alone
    for i in range(1, 5):
        result = leveling.apply_progress(state, earned_xp=0.0)
        assert result.level_ups == [], f"should not level up on activity {i}"
        state = result.state

    result = leveling.apply_progress(state, earned_xp=0.0)
    assert len(result.level_ups) == 1, "must level up on the 5th activity regardless of XP"
    assert result.state.level == 2
    assert result.state.activities_this_level == 0


def test_apply_progress_never_exceeds_ten_activities_per_level_even_with_tiny_xp() -> None:
    state = _fresh_state(level=30, ema=500.0)  # activities_to_next_level(30) == 10
    for _ in range(9):
        result = leveling.apply_progress(state, earned_xp=0.01)
        assert result.level_ups == []
        state = result.state

    result = leveling.apply_progress(state, earned_xp=0.01)
    assert len(result.level_ups) == 1
    assert state.activities_this_level == 9


def test_simulated_progression_never_violates_five_to_ten_guarantee() -> None:
    """Property-style check over a long randomized progression.

    The hard, structural invariant is the upper bound: a level must never
    take more than 10 activities, no matter how unlucky the XP variance is
    -- checked on every single level-up below. The lower bound of 5 is a
    typical-case expectation, not a hard per-instance guarantee (a streak of
    unusually strong activities can legitimately clear a level a little
    early, which is a feature, not a bug), so it's checked in aggregate
    across the whole simulated run instead.
    """
    rng = random.Random(42)
    state = leveling.LevelingState(
        level=1,
        xp_into_level=0.0,
        xp_to_next_level_snapshot=leveling.activities_to_next_level(1) * 80.0,
        activities_this_level=0,
        avg_xp_per_activity_ema=80.0,
    )

    activities_since_last_level = 0
    levels_reached = 0
    activities_per_level_samples: list[int] = []

    for _ in range(3000):
        if levels_reached >= 60:
            break
        # Simulate realistic, noisy XP yields per activity.
        earned = max(0.0, rng.gauss(mu=90, sigma=40))
        activities_since_last_level += 1
        result = leveling.apply_progress(state, earned)
        state = result.state

        if result.level_ups:
            # Hard upper bound: must never be violated, even inside a cascade.
            assert activities_since_last_level <= 10, (
                f"level-up after {activities_since_last_level} activities, expected <= 10"
            )
            activities_per_level_samples.append(activities_since_last_level)
            levels_reached += len(result.level_ups)
            activities_since_last_level = 0

    assert levels_reached >= 60, "simulation should have reached the target number of level-ups"
    average_activities_per_level = sum(activities_per_level_samples) / len(activities_per_level_samples)
    assert 5 <= average_activities_per_level <= 10, (
        f"average activities/level was {average_activities_per_level}, expected roughly [5, 10]"
    )
