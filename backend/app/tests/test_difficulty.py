import pytest

from app.services.course_engine import difficulty


def test_compute_difficulty_rating_matches_plan_worked_example_low_endurance() -> None:
    # 6,000m effective distance / capacity 4,200 (endurance level 3) -> 30
    rating = difficulty.compute_difficulty_rating(distance_meters=6000.0, elevation_gain_meters=0.0, endurance_skill_level=3)
    assert rating == 30


def test_compute_difficulty_rating_matches_plan_worked_example_high_endurance() -> None:
    # 6,000m effective distance / capacity 11,000 (endurance level 20) -> 12
    rating = difficulty.compute_difficulty_rating(distance_meters=6000.0, elevation_gain_meters=0.0, endurance_skill_level=20)
    assert rating == 12


def test_compute_difficulty_rating_same_course_differs_by_user() -> None:
    low = difficulty.compute_difficulty_rating(5000.0, 100.0, endurance_skill_level=1)
    high = difficulty.compute_difficulty_rating(5000.0, 100.0, endurance_skill_level=30)
    assert low > high


def test_compute_difficulty_rating_elevation_increases_difficulty() -> None:
    flat = difficulty.compute_difficulty_rating(5000.0, 0.0, endurance_skill_level=5)
    hilly = difficulty.compute_difficulty_rating(5000.0, 300.0, endurance_skill_level=5)
    assert hilly > flat


def test_compute_difficulty_rating_clamped_to_valid_range() -> None:
    assert difficulty.compute_difficulty_rating(1.0, 0.0, endurance_skill_level=1000) >= difficulty.MIN_DIFFICULTY
    assert difficulty.compute_difficulty_rating(1_000_000.0, 50_000.0, endurance_skill_level=1) <= difficulty.MAX_DIFFICULTY
