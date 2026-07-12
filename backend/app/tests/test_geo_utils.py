import pytest

from app.services.geo_utils import haversine_distance_meters


def test_haversine_distance_zero_for_same_point() -> None:
    assert haversine_distance_meters(38.88, -77.09, 38.88, -77.09) == pytest.approx(0.0, abs=1e-6)


def test_haversine_distance_known_value() -> None:
    # Roughly 1 degree of latitude at the equator is ~111.19 km.
    distance = haversine_distance_meters(0.0, 0.0, 1.0, 0.0)
    assert distance == pytest.approx(111_195, rel=0.01)


def test_haversine_distance_is_symmetric() -> None:
    a = haversine_distance_meters(38.86, -77.05, 38.87, -77.04)
    b = haversine_distance_meters(38.87, -77.04, 38.86, -77.05)
    assert a == pytest.approx(b)
