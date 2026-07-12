import pytest

from app.services.course_engine import matching


def _straight_line(start_lat: float, start_lon: float, end_lat: float, end_lon: float, n: int) -> list[dict]:
    return [
        {"lat": start_lat + (end_lat - start_lat) * i / (n - 1), "lon": start_lon + (end_lon - start_lon) * i / (n - 1)}
        for i in range(n)
    ]


def test_encode_point_is_deterministic() -> None:
    assert matching.encode_point(38.8632, -77.0481) == matching.encode_point(38.8632, -77.0481)


def test_neighbor_geohashes_includes_self_and_eight_neighbors() -> None:
    cells = matching.neighbor_geohashes("dqcjndz")
    assert "dqcjndz" in cells
    assert len(cells) == 9


def test_polyline_similarity_score_near_zero_for_identical_route() -> None:
    route = _straight_line(38.86, -77.05, 38.87, -77.04, 50)
    score = matching.polyline_similarity_score(route, route)
    assert score == pytest.approx(0.0, abs=1.0)


def test_polyline_similarity_score_high_for_very_different_routes() -> None:
    route_a = _straight_line(38.86, -77.05, 38.87, -77.04, 50)
    route_b = _straight_line(40.71, -74.00, 40.72, -74.01, 50)  # roughly NYC
    score = matching.polyline_similarity_score(route_a, route_b)
    assert score > 100_000  # very far apart


def test_polyline_similarity_score_robust_to_different_point_counts() -> None:
    # Same physical route, sampled at different densities (e.g. different GPS
    # recording rates) -- should still resample down to a comparable score.
    dense = _straight_line(38.86, -77.05, 38.87, -77.04, 500)
    sparse = _straight_line(38.86, -77.05, 38.87, -77.04, 8)
    score = matching.polyline_similarity_score(dense, sparse)
    assert score == pytest.approx(0.0, abs=5.0)


def test_is_match_true_for_same_route_same_distance() -> None:
    route = _straight_line(38.86, -77.05, 38.87, -77.04, 50)
    matched, score = matching.is_match(route, 1000.0, route, 1000.0)
    assert matched is True
    assert score == pytest.approx(0.0, abs=1.0)


def test_is_match_false_when_distance_differs_too_much() -> None:
    route = _straight_line(38.86, -77.05, 38.87, -77.04, 50)
    matched, _ = matching.is_match(route, 1000.0, route, 1500.0)  # 50% longer
    assert matched is False


def test_is_match_false_for_geographically_different_routes() -> None:
    route_a = _straight_line(38.86, -77.05, 38.87, -77.04, 50)
    route_b = _straight_line(40.71, -74.00, 40.72, -74.01, 50)
    matched, _ = matching.is_match(route_a, 1000.0, route_b, 1000.0)
    assert matched is False


def test_is_match_tolerates_small_boundary_drift() -> None:
    route_a = _straight_line(38.86000, -77.05000, 38.87000, -77.04000, 50)
    # Same route, shifted by ~0.0001 degrees (~10m) -- should still match.
    route_b = _straight_line(38.86010, -77.05010, 38.87010, -77.04010, 50)
    matched, score = matching.is_match(route_a, 1000.0, route_b, 1000.0)
    assert matched is True
    assert score < matching.MAX_MEAN_POINT_DISTANCE_METERS
