"""Orchestrates one activity -> matched/created course, personalized
difficulty (frozen at discovery), and course-mastery leveling progress.

Reuses xp_engine.leveling verbatim, exactly as main/skill leveling do, with
each course tracking its own independent CourseUserProgress row and EMA.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.course import Course
from app.models.course_activity_link import CourseActivityLink
from app.models.course_user_progress import CourseUserProgress
from app.models.skill import Skill
from app.models.skill_progress import SkillProgress
from app.models.user import User
from app.models.xp_transaction import XPTransaction
from app.services.course_engine import difficulty, matching
from app.services.region_engine import region_service
from app.services.xp_engine import leveling

FORMULA_VERSION = 1
COURSE_XP_BASE = 200.0
REPEAT_DECAY_PER_RUN = 0.05
REPEAT_DECAY_FLOOR = 0.3


@dataclass
class CourseProcessingResult:
    course: Course | None
    is_new_discovery: bool
    difficulty_rating: int | None
    level_ups: list[leveling.LevelUpEvent]


async def process_activity_course(db: AsyncSession, user: User, activity: Activity) -> CourseProcessingResult:
    """No-ops gracefully when the activity has no usable GPS data (e.g. an
    indoor workout) -- course leveling is additive, not a blocker."""
    if not activity.polyline or len(activity.polyline) < 2 or not activity.start_point or not activity.end_point:
        return CourseProcessingResult(course=None, is_new_discovery=False, difficulty_rating=None, level_ups=[])

    start_geohash = matching.encode_point(activity.start_point["lat"], activity.start_point["lon"])
    end_geohash = matching.encode_point(activity.end_point["lat"], activity.end_point["lon"])
    activity.start_geohash = start_geohash
    activity.end_geohash = end_geohash

    candidate_cells = matching.neighbor_geohashes(start_geohash)
    candidates = list(
        await db.scalars(
            select(Course).where(
                Course.activity_type == activity.activity_type,
                Course.start_geohash.in_(candidate_cells),
            )
        )
    )

    course = None
    best_score = None
    for candidate in candidates:
        matched, score = matching.is_match(
            candidate.canonical_polyline, candidate.distance_meters, activity.polyline, activity.distance_meters
        )
        if matched and (best_score is None or score < best_score):
            course = candidate
            best_score = score

    is_new_discovery = course is None

    if course is None:
        region = await region_service.get_or_create_region_for_point(
            db,
            activity.start_point["lat"],
            activity.start_point["lon"],
            f"course discovery at {activity.start_point['lat']:.4f},{activity.start_point['lon']:.4f}",
        )
        course = Course(
            region_id=region.id,
            activity_type=activity.activity_type,
            name=activity.activity_name or f"{activity.activity_type.title()} Course",
            canonical_polyline=activity.polyline,
            start_geohash=start_geohash,
            end_geohash=end_geohash,
            distance_meters=activity.distance_meters,
            elevation_gain_meters=activity.elevation_gain_meters,
            discovery_count=1,
        )
        db.add(course)
        await db.flush()
        best_score = 0.0
    else:
        course.discovery_count += 1

    activity.course_id = course.id
    db.add(CourseActivityLink(course_id=course.id, activity_id=activity.id, similarity_score=best_score or 0.0))

    progress = await db.scalar(
        select(CourseUserProgress).where(
            CourseUserProgress.user_id == user.id, CourseUserProgress.course_id == course.id
        )
    )

    if progress is None:
        endurance_level = await _current_endurance_level(db, user)
        difficulty_rating = difficulty.compute_difficulty_rating(
            course.distance_meters, course.elevation_gain_meters, endurance_level
        )
        seed = leveling.initial_state()
        progress = CourseUserProgress(
            user_id=user.id,
            course_id=course.id,
            difficulty_rating_at_discovery=difficulty_rating,
            level=seed.level,
            xp_into_level=seed.xp_into_level,
            xp_to_next_level_snapshot=seed.xp_to_next_level_snapshot,
            activities_this_level=seed.activities_this_level,
            avg_xp_per_activity_ema=seed.avg_xp_per_activity_ema,
            times_run=0,
        )
        db.add(progress)
    else:
        difficulty_rating = progress.difficulty_rating_at_discovery

    repeat_decay = max(REPEAT_DECAY_FLOOR, 1 - REPEAT_DECAY_PER_RUN * progress.times_run)
    progress.times_run += 1
    if progress.best_time_seconds is None or activity.duration_seconds < progress.best_time_seconds:
        progress.best_time_seconds = activity.duration_seconds

    course_xp = round(COURSE_XP_BASE * repeat_decay)

    state = leveling.LevelingState(
        level=progress.level,
        xp_into_level=progress.xp_into_level,
        xp_to_next_level_snapshot=progress.xp_to_next_level_snapshot,
        activities_this_level=progress.activities_this_level,
        avg_xp_per_activity_ema=progress.avg_xp_per_activity_ema,
    )
    result = leveling.apply_progress(state, course_xp)
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
            xp_type="course",
            target_key=str(course.id),
            base_xp=COURSE_XP_BASE,
            multipliers={"repeat_decay": repeat_decay},
            final_xp=course_xp,
            formula_version=FORMULA_VERSION,
            level_before=level_before,
            level_after=result.state.level,
        )
    )

    return CourseProcessingResult(
        course=course,
        is_new_discovery=is_new_discovery,
        difficulty_rating=difficulty_rating,
        level_ups=result.level_ups,
    )


async def _current_endurance_level(db: AsyncSession, user: User) -> int:
    endurance_skill = await db.scalar(select(Skill).where(Skill.key == "endurance"))
    if endurance_skill is None:
        return 1
    progress = await db.scalar(
        select(SkillProgress).where(SkillProgress.user_id == user.id, SkillProgress.skill_id == endurance_skill.id)
    )
    return progress.level if progress is not None else 1
