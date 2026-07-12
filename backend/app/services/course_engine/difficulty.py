"""Personalized course difficulty -- the mechanism that makes no two users
level the same course identically.

Deliberately distinct from course MASTERY (course_user_progress.level, which
only ever goes up as the user repeats a route): this difficulty rating is
computed once, at discovery, from the route's grade-adjusted distance
relative to THIS user's current Endurance skill capacity, then frozen.
"""

MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 99
BASE_CAPACITY_METERS = 3000.0
CAPACITY_PER_ENDURANCE_LEVEL = 400.0
GRADE_ADJUSTMENT_PER_METER_GAIN = 10.0


def compute_difficulty_rating(distance_meters: float, elevation_gain_meters: float, endurance_skill_level: int) -> int:
    effective_distance = distance_meters + elevation_gain_meters * GRADE_ADJUSTMENT_PER_METER_GAIN
    user_capacity = BASE_CAPACITY_METERS + endurance_skill_level * CAPACITY_PER_ENDURANCE_LEVEL
    if user_capacity <= 0:
        user_capacity = BASE_CAPACITY_METERS
    rating = round(1 + 20 * (effective_distance / user_capacity))
    return max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, rating))
