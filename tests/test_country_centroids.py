"""Tests for country_centroids shared utility."""

from src.country_centroids import get_centroid, CENTROIDS


def test_known_country():
    result = get_centroid("Bangladesh")
    assert result is not None
    lat, lon = result
    assert abs(lat - 24.0) < 1.0
    assert abs(lon - 90.0) < 1.0


def test_case_insensitive():
    result = get_centroid("BANGLADESH")
    assert result is not None


def test_alternate_name():
    result = get_centroid("USA")
    assert result is not None
    lat, lon = result
    assert abs(lat - 39.8) < 1.0


def test_unknown_country():
    result = get_centroid("Atlantis")
    assert result is None


def test_invalid_input_returns_none():
    assert get_centroid("") is None
    assert get_centroid(None) is None


def test_drc():
    result = get_centroid("Democratic Republic of the Congo")
    assert result is not None


def test_palestine():
    result = get_centroid("Palestine")
    assert result is not None
