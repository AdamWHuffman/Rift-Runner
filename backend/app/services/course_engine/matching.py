"""Route matching: geohash-bucket candidate retrieval + polyline similarity.

Coarse retrieval via geohash buckets keeps this cheap even as course counts
grow; the actual match/no-match decision comes from resampling both
polylines to N evenly-spaced points and checking mean point distance plus a
distance-delta check -- a concrete, cheap stand-in for full Frechet/DTW
matching (a flagged upgrade if false matches ever become a real problem).
"""

import pygeohash as pgh

from app.services.geo_utils import haversine_distance_meters

GEOHASH_PRECISION = 7
RESAMPLE_POINTS = 20
MAX_MEAN_POINT_DISTANCE_METERS = 60.0
MAX_DISTANCE_DELTA_RATIO = 0.15


def encode_point(lat: float, lon: float) -> str:
    return pgh.encode(lat, lon, precision=GEOHASH_PRECISION)


def neighbor_geohashes(geohash: str) -> set[str]:
    """The geohash cell itself plus its 8 surrounding cells, to absorb
    boundary drift between GPS traces of the same real-world route."""
    cells = {geohash}
    for direction in ("top", "bottom", "left", "right"):
        cells.add(pgh.get_adjacent(geohash, direction))
    for vertical in ("top", "bottom"):
        for horizontal in ("left", "right"):
            cells.add(pgh.get_adjacent(pgh.get_adjacent(geohash, vertical), horizontal))
    return cells


def _resample(polyline: list[dict[str, float]], n: int) -> list[tuple[float, float]]:
    """Resample a polyline to n evenly-spaced points by cumulative distance."""
    if len(polyline) < 2:
        point = (polyline[0]["lat"], polyline[0]["lon"]) if polyline else (0.0, 0.0)
        return [point] * n

    cumulative = [0.0]
    for i in range(1, len(polyline)):
        d = haversine_distance_meters(
            polyline[i - 1]["lat"], polyline[i - 1]["lon"], polyline[i]["lat"], polyline[i]["lon"]
        )
        cumulative.append(cumulative[-1] + d)

    total = cumulative[-1]
    if total == 0:
        return [(polyline[0]["lat"], polyline[0]["lon"])] * n

    targets = [total * i / (n - 1) for i in range(n)]
    result: list[tuple[float, float]] = []
    j = 0
    for target in targets:
        while j < len(cumulative) - 2 and cumulative[j + 1] < target:
            j += 1
        segment_len = cumulative[j + 1] - cumulative[j]
        t = (target - cumulative[j]) / segment_len if segment_len > 0 else 0.0
        lat = polyline[j]["lat"] + t * (polyline[j + 1]["lat"] - polyline[j]["lat"])
        lon = polyline[j]["lon"] + t * (polyline[j + 1]["lon"] - polyline[j]["lon"])
        result.append((lat, lon))
    return result


def polyline_similarity_score(polyline_a: list[dict[str, float]], polyline_b: list[dict[str, float]]) -> float:
    """Mean point-to-point distance in meters after resampling both to N
    evenly-spaced points -- lower means more similar."""
    resampled_a = _resample(polyline_a, RESAMPLE_POINTS)
    resampled_b = _resample(polyline_b, RESAMPLE_POINTS)
    distances = [haversine_distance_meters(a[0], a[1], b[0], b[1]) for a, b in zip(resampled_a, resampled_b)]
    return sum(distances) / len(distances)


def is_match(
    candidate_polyline: list[dict[str, float]],
    candidate_distance_meters: float,
    activity_polyline: list[dict[str, float]],
    activity_distance_meters: float,
) -> tuple[bool, float]:
    """Returns (is_match, similarity_score). The score is always returned,
    even on a non-match, so callers can log/store it for later review."""
    score = polyline_similarity_score(candidate_polyline, activity_polyline)
    if candidate_distance_meters <= 0:
        return False, score
    distance_delta_ratio = abs(activity_distance_meters - candidate_distance_meters) / candidate_distance_meters
    matched = score < MAX_MEAN_POINT_DISTANCE_METERS and distance_delta_ratio < MAX_DISTANCE_DELTA_RATIO
    return matched, score
