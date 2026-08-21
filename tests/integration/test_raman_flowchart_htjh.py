"""Integration test locking in the 'exalted lord in dusthana' HTJH fix.

Regression case: Leo Lagna, 5th lord Jupiter exalted in Cancer, placed in
H12 (dusthana). Before the fix, this landed as "concern" purely from a
tie-break bug in _status3 plus a scoring model that treated an exalted
lord's dusthana placement as unconditionally negative, contradicting the
HTJH principle that an exalted/strong lord's significations are redirected,
not denied. Jupiter here also rules H8 (dusthana) placed in H12 (dusthana),
forming Viparita Raja Yoga — the H5 finding should reference it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from vedic_ai.domain.birth import BirthData, GeoLocation
from vedic_ai.features.core_features import extract_core_features

swisseph = pytest.importorskip("swisseph")


@pytest.fixture(scope="module")
def h5_step() -> dict:
    from vedic_ai.engines.base import compute_core_chart
    from vedic_ai.engines.swisseph_adapter import SwissEphAdapter

    tz = timezone(timedelta(hours=5, minutes=30))
    birth = BirthData(
        birth_datetime=datetime(2003, 7, 9, 10, 10, tzinfo=tz),
        location=GeoLocation(latitude=21.1458, longitude=79.0882, place_name="Nagpur"),
        name="Sample",
    )
    bundle = compute_core_chart(birth, SwissEphAdapter())
    features = extract_core_features(bundle)

    assert features["lagna"]["rasi"] == "Leo"
    assert features["planets"]["Jupiter"]["dignity"] == "exalted"
    assert features["planets"]["Jupiter"]["house"] == 12
    assert features["houses"][5]["lord"] == "Jupiter"

    m4 = next(m for m in features["flowchart"]["modules"] if m["id"] == "M4")
    return next(s for s in m4["steps"] if s["id"] == "4.5")


class TestExaltedDusthanaLordRedirection:
    def test_status_is_not_concern(self, h5_step):
        assert h5_step["status"] != "concern"

    def test_modification_not_denial_present(self, h5_step):
        assert any("MODIFICATION, NOT DENIAL" in f for f in h5_step["findings"])

    def test_no_contradictory_flat_denial_finding(self, h5_step):
        assert not any(
            "difficulty with children or creative expression" in f
            for f in h5_step["findings"]
        )

    def test_viparita_raja_yoga_cross_referenced(self, h5_step):
        assert any("Viparita Raja Yoga" in f for f in h5_step["findings"])
