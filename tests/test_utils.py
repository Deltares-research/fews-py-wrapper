from datetime import datetime, timezone

import pytest

from fews_py_wrapper.utils import format_datetime


def test_format_datetime():
    dt_aware = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    formatted = format_datetime(dt_aware)
    assert formatted == "2023-01-01T12:00:00Z"

    dt_non_aware = datetime(2023, 1, 1, 12, 0, 0)
    with pytest.raises(
        ValueError, match="Datetime object must be timezone-aware."
    ):
        format_datetime(dt_non_aware)
