"""Tests for NASA FIRMS (Fire Information for Resource Management System) adapter."""

import csv
import io
import pytest
from unittest.mock import patch

from src.firms import (
    scrape_firms,
    _cluster_severity,
    _cluster_human_interest,
    _grid_key,
    _nearest_country,
    _parse_confidence,
    _parse_detections,
    _cluster_detections,
    _build_event_signature,
    _build_title,
    _build_summary,
    _fetch_firms_csv,
)


# --- Severity mapping tests ---

@pytest.mark.parametrize("count,expected", [
    (1, 1), (2, 1),       # small
    (3, 2), (10, 2),      # moderate
    (11, 3), (50, 3),     # large
    (51, 4), (200, 4),    # major
    (201, 5), (1000, 5),  # extreme
])
def test_severity(count, expected):
    assert _cluster_severity(count) == expected


# --- Human interest mapping tests ---

@pytest.mark.parametrize("count,expected", [
    (1, 2), (2, 2),       # small
    (5, 3), (10, 4),      # medium
    (50, 6), (100, 7),    # large
    (200, 8), (500, 9),   # major
    (501, 10), (1000, 10), # extreme
])
def test_human_interest(count, expected):
    assert _cluster_human_interest(count) == expected


# --- Grid key tests ---

def test_grid_key_positive():
    key = _grid_key(34.2, -118.7)
    assert key == (34.0, -119.0)


def test_grid_key_negative():
    key = _grid_key(-15.3, 28.8)
    assert key == (-15.5, 28.5)


def test_grid_key_zero():
    key = _grid_key(0.1, 0.1)
    assert key == (0.0, 0.0)


def test_grid_key_boundary():
    key = _grid_key(34.5, -118.5)
    assert key == (34.5, -118.5)


# --- Nearest country tests ---

def test_nearest_country_usa():
    country = _nearest_country(40.0, -100.0)
    assert country is not None
    assert "United States" in country or "America" in country


def test_nearest_country_australia():
    country = _nearest_country(-25.0, 135.0)
    assert country is not None
    assert "Australia" in country


def test_nearest_country_ocean():
    """Middle of Pacific should return None."""
    country = _nearest_country(0.0, -160.0)
    assert country is None


def test_nearest_country_brazil():
    country = _nearest_country(-10.0, -55.0)
    assert country is not None
    assert "Brazil" in country


# --- Confidence parsing tests ---

@pytest.mark.parametrize("value,expected", [
    ("high", 95),
    ("nominal", 80),
    ("low", 30),
    ("85", 85),
    ("HIGH", 95),
    ("Nominal", 80),
])
def test_parse_confidence(value, expected):
    assert _parse_confidence(value) == expected


def test_parse_confidence_empty():
    assert _parse_confidence("") is None
    assert _parse_confidence(None) is None


# --- CSV parsing tests ---

def _make_csv_text(rows):
    """Build a FIRMS-format CSV string from list of row dicts."""
    if not rows:
        return ""
    fieldnames = ["latitude", "longitude", "brightness", "scan", "track",
                  "acq_date", "acq_time", "satellite", "instrument",
                  "confidence", "version", "bright_t31", "frp", "daynight", "type"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        full_row = {f: "" for f in fieldnames}
        full_row.update(row)
        writer.writerow(full_row)
    return output.getvalue()


def test_parse_detections_filters_low_confidence():
    csv_text = _make_csv_text([
        {"latitude": "34.0", "longitude": "-118.0", "confidence": "low", "frp": "10.0",
         "acq_date": "2026-03-14", "acq_time": "1200"},
        {"latitude": "35.0", "longitude": "-117.0", "confidence": "high", "frp": "20.0",
         "acq_date": "2026-03-14", "acq_time": "1200"},
    ])
    detections = _parse_detections(csv_text)
    assert len(detections) == 1
    assert detections[0]["lat"] == 35.0


def test_parse_detections_filters_numeric_confidence():
    csv_text = _make_csv_text([
        {"latitude": "34.0", "longitude": "-118.0", "confidence": "50", "frp": "10.0",
         "acq_date": "2026-03-14", "acq_time": "1200"},
        {"latitude": "35.0", "longitude": "-117.0", "confidence": "90", "frp": "20.0",
         "acq_date": "2026-03-14", "acq_time": "1200"},
    ])
    detections = _parse_detections(csv_text)
    assert len(detections) == 1
    assert detections[0]["confidence"] == 90


def test_parse_detections_nominal_passes():
    csv_text = _make_csv_text([
        {"latitude": "34.0", "longitude": "-118.0", "confidence": "nominal", "frp": "10.0",
         "acq_date": "2026-03-14", "acq_time": "1200"},
    ])
    detections = _parse_detections(csv_text)
    assert len(detections) == 1


def test_parse_detections_empty():
    assert _parse_detections("") == []
    assert _parse_detections(None) == []


def test_parse_detections_header_only():
    csv_text = "latitude,longitude,brightness,confidence,frp,acq_date,acq_time\n"
    detections = _parse_detections(csv_text)
    assert len(detections) == 0


def test_parse_detections_zero_coords():
    csv_text = _make_csv_text([
        {"latitude": "0", "longitude": "0", "confidence": "high", "frp": "10.0",
         "acq_date": "2026-03-14", "acq_time": "1200"},
    ])
    detections = _parse_detections(csv_text)
    assert len(detections) == 0


def test_parse_detections_frp_extraction():
    csv_text = _make_csv_text([
        {"latitude": "34.0", "longitude": "-118.0", "confidence": "high", "frp": "42.5",
         "acq_date": "2026-03-14", "acq_time": "1200"},
    ])
    detections = _parse_detections(csv_text)
    assert len(detections) == 1
    assert detections[0]["frp"] == 42.5


# --- Cluster tests ---

def test_cluster_nearby_detections():
    """Detections in same grid cell should cluster together."""
    detections = [
        {"lat": 34.1, "lon": -118.1, "frp": 10.0, "acq_date": "2026-03-14", "confidence": 90},
        {"lat": 34.2, "lon": -118.2, "frp": 20.0, "acq_date": "2026-03-14", "confidence": 95},
        {"lat": 34.3, "lon": -118.3, "frp": 30.0, "acq_date": "2026-03-14", "confidence": 85},
    ]
    clusters = _cluster_detections(detections)
    assert len(clusters) == 1
    key = list(clusters.keys())[0]
    assert clusters[key]["count"] == 3
    assert clusters[key]["max_frp"] == 30.0


def test_cluster_distant_detections():
    """Detections in different grid cells should form separate clusters."""
    detections = [
        {"lat": 34.1, "lon": -118.1, "frp": 10.0, "acq_date": "2026-03-14", "confidence": 90},
        {"lat": -25.0, "lon": 135.0, "frp": 20.0, "acq_date": "2026-03-14", "confidence": 95},
    ]
    clusters = _cluster_detections(detections)
    assert len(clusters) == 2


def test_cluster_avg_coordinates():
    """Cluster should have average coordinates."""
    detections = [
        {"lat": 34.1, "lon": -118.1, "frp": 10.0, "acq_date": "2026-03-14", "confidence": 90},
        {"lat": 34.3, "lon": -118.3, "frp": 20.0, "acq_date": "2026-03-14", "confidence": 95},
    ]
    clusters = _cluster_detections(detections)
    # Both at grid key (34.0, -118.5), should form one cluster
    assert len(clusters) == 1
    key = list(clusters.keys())[0]
    assert abs(clusters[key]["avg_lat"] - 34.2) < 0.01
    assert abs(clusters[key]["avg_lon"] - (-118.2)) < 0.01


def test_cluster_keeps_latest_date():
    """Cluster should keep the latest acquisition date."""
    detections = [
        {"lat": 34.1, "lon": -118.1, "frp": 10.0, "acq_date": "2026-03-13", "confidence": 90},
        {"lat": 34.2, "lon": -118.2, "frp": 20.0, "acq_date": "2026-03-14", "confidence": 95},
    ]
    clusters = _cluster_detections(detections)
    key = list(clusters.keys())[0]
    assert clusters[key]["date"] == "2026-03-14"


def test_cluster_empty():
    clusters = _cluster_detections([])
    assert len(clusters) == 0


# --- Event signature tests ---

def test_event_signature_with_country():
    sig = _build_event_signature(34.0, -118.0, "United States")
    assert "United States" in sig
    assert "Wildfire" in sig


def test_event_signature_no_country():
    sig = _build_event_signature(34.0, -118.0, None)
    assert "Fire" in sig
    assert "N34" in sig
    assert "W118" in sig


def test_event_signature_southern_hemisphere():
    sig = _build_event_signature(-25.0, 135.0, None)
    assert "S25" in sig
    assert "E135" in sig


# --- Title tests ---

def test_title_with_country_large():
    title = _build_title(100, "Australia", -25.0, 135.0)
    assert "Australia" in title
    assert "wildfire" in title.lower() or "Major" in title


def test_title_with_country_small():
    title = _build_title(2, "Brazil", -10.0, -55.0)
    assert "Brazil" in title
    assert "detected" in title.lower()


def test_title_no_country():
    title = _build_title(5, None, 34.0, -118.0)
    assert "N34.0" in title or "34.0" in title


# --- Summary tests ---

def test_summary_content():
    summary = _build_summary(25, 42.5, "Australia", "2026-03-14")
    assert "25 fire detections" in summary
    assert "Australia" in summary
    assert "42.5 MW" in summary
    assert "2026-03-14" in summary


def test_summary_single_detection():
    summary = _build_summary(1, 10.0, "Brazil", "2026-03-14")
    assert "1 fire detection " in summary  # singular, no trailing 's'


def test_summary_no_country():
    summary = _build_summary(5, 0, None, "2026-03-14")
    assert "5 fire detections" in summary
    assert "Location" not in summary


# --- Graceful skip when no API key ---

def test_skip_no_api_key():
    with patch("src.firms.FIRMS_API_KEY", ""):
        stories = scrape_firms()
    assert stories == []


# --- Full scrape tests ---

def _make_firms_csv(detections):
    """Build FIRMS CSV from detection tuples (lat, lon, confidence, frp, date)."""
    lines = ["latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight,type"]
    for lat, lon, conf, frp, date in detections:
        lines.append("%.4f,%.4f,300.0,0.4,0.4,%s,1200,N,VIIRS,%s,2.0,280.0,%.1f,D,0" % (
            lat, lon, date, conf, frp))
    return "\n".join(lines)


def test_scrape_firms_basic():
    csv_text = _make_firms_csv([
        (34.1, -118.1, "high", 10.0, "2026-03-14"),
        (34.2, -118.2, "high", 20.0, "2026-03-14"),
    ])
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 1  # Same grid cell -> 1 story
    s = stories[0]
    assert s["origin"] == "firms"
    assert s["source_type"] == "inferred"
    assert s["category"] == "disaster"
    assert "wildfire" in s["concepts"]
    assert "fire" in s["concepts"]


def test_scrape_firms_multiple_clusters():
    csv_text = _make_firms_csv([
        (34.1, -118.1, "high", 10.0, "2026-03-14"),
        (-25.0, 135.0, "high", 20.0, "2026-03-14"),
    ])
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 2


def test_scrape_firms_confidence_filtering():
    csv_text = _make_firms_csv([
        (34.1, -118.1, "high", 10.0, "2026-03-14"),
        (35.0, -117.0, "low", 20.0, "2026-03-14"),
    ])
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 1  # Low confidence filtered out


def test_scrape_firms_empty_csv():
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=""):
            stories = scrape_firms()

    assert stories == []


# --- Story dict shape tests ---

def test_story_dict_shape():
    csv_text = _make_firms_csv([
        (34.1, -118.1, "high", 15.0, "2026-03-14"),
        (34.2, -118.2, "high", 25.0, "2026-03-14"),
        (34.15, -118.15, "nominal", 12.0, "2026-03-14"),
    ])
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 1
    s = stories[0]

    # Required story fields
    assert "title" in s and len(s["title"]) > 0
    assert s["url"].startswith("https://firms.modaps.eosdis.nasa.gov/fire/")
    assert "summary" in s
    assert s["source"] == "NASA FIRMS"
    assert s["origin"] == "firms"
    assert s["source_type"] == "inferred"
    assert s["category"] == "disaster"
    assert s["concepts"] == ["wildfire", "fire", "environment", "climate"]
    assert s["lat"] is not None
    assert s["lon"] is not None
    assert s["geocode_confidence"] == 1.0
    assert s["published_at"] is not None

    # Extraction data
    ext = s["_extraction"]
    assert "event_signature" in ext
    assert isinstance(ext["topics"], list)
    assert "wildfire" in ext["topics"]
    assert ext["severity"] == 2  # 3 detections = severity 2
    assert ext["location_type"] == "terrestrial"
    assert ext["human_interest_score"] == 3  # 3 detections
    assert isinstance(ext["actors"], list)
    assert isinstance(ext["locations"], list)
    assert len(ext["locations"]) == 1
    assert ext["locations"][0]["role"] == "event_location"
    assert "FIRMS" in ext["search_keywords"]


# --- Dedup tests ---

def test_dedup_url_includes_date():
    """Dedup URL includes date for daily uniqueness."""
    csv_text = _make_firms_csv([
        (34.1, -118.1, "high", 10.0, "2026-03-14"),
    ])
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 1
    assert "2026-03-14" in stories[0]["url"]


# --- Severity mapping in context ---

def test_severity_from_cluster_size():
    """Severity should scale with number of detections in cluster."""
    # Create 55 detections in same grid cell -> severity 4
    detections = [(34.1 + i * 0.001, -118.1 + i * 0.001, "high", 10.0, "2026-03-14")
                  for i in range(55)]
    csv_text = _make_firms_csv(detections)
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 1
    assert stories[0]["_extraction"]["severity"] == 4


# --- Large volume handling test ---

def test_large_volume_clustering():
    """Many detections should cluster down to manageable number of stories."""
    # 500 detections spread across 5 grid cells (100 each)
    detections = []
    for cell_idx in range(5):
        base_lat = 20.0 + cell_idx * 5.0
        base_lon = -100.0 + cell_idx * 5.0
        for i in range(100):
            detections.append((
                base_lat + i * 0.001,
                base_lon + i * 0.001,
                "high", 10.0, "2026-03-14"
            ))

    csv_text = _make_firms_csv(detections)
    with patch("src.firms.FIRMS_API_KEY", "test_key"):
        with patch("src.firms._fetch_firms_csv", return_value=csv_text):
            stories = scrape_firms()

    assert len(stories) == 5  # 5 grid cells = 5 stories
    # Each should have severity 4 (51-200)
    for s in stories:
        assert s["_extraction"]["severity"] == 4


# --- FIRMS_MAX_ROWS cap tests ---

def test_max_rows_caps_detections():
    """Detections exceeding FIRMS_MAX_ROWS should be capped."""
    # Create 20 high-confidence detections
    rows = [(34.0 + i * 0.01, -118.0 + i * 0.01, "high", 10.0, "2026-03-14")
            for i in range(20)]
    csv_text = _make_firms_csv(rows)

    with patch("src.firms.FIRMS_MAX_ROWS", 5):
        detections = _parse_detections(csv_text)
    assert len(detections) == 5


def test_max_rows_only_counts_high_confidence():
    """FIRMS_MAX_ROWS cap only counts rows that pass confidence filter."""
    rows = [
        (34.0, -118.0, "high", 10.0, "2026-03-14"),
        (34.1, -118.1, "low", 10.0, "2026-03-14"),   # filtered out
        (34.2, -118.2, "high", 10.0, "2026-03-14"),
        (34.3, -118.3, "low", 10.0, "2026-03-14"),   # filtered out
        (34.4, -118.4, "high", 10.0, "2026-03-14"),
    ]
    csv_text = _make_firms_csv(rows)

    with patch("src.firms.FIRMS_MAX_ROWS", 2):
        detections = _parse_detections(csv_text)
    # Cap of 2 applies to high-confidence rows only
    assert len(detections) == 2


