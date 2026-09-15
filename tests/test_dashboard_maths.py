"""Display arithmetic. Pure functions, no socket, no subprocess."""
import pytest

from riskdesk.dashboard import maths

pytestmark = pytest.mark.unit


def test_a_ratio_that_cannot_be_computed_is_not_zero():
    """Zero leverage and unknown leverage are different facts, and only one
    of them describes a book with no exposure."""
    assert maths.safe_ratio(10, 0) is None
    assert maths.safe_ratio(10, None) is None
    assert maths.safe_ratio(None, 10) is None
    assert maths.safe_ratio(10, 4) == 2.5


def test_a_ratio_that_overflows_is_refused():
    assert maths.safe_ratio(1e308, 1e-308) is None


def test_a_small_position_keeps_a_visible_bar():
    """A bar rounded to nothing reads as an absent position."""
    assert maths.bar_width(1, 1_000_000, 400) == pytest.approx(1.0)
    assert maths.bar_width(500_000, 1_000_000, 400) == pytest.approx(200.0)


def test_an_exact_zero_gets_no_width_from_here():
    """The caller decides how to draw nothing; a one-pixel bar would claim
    a direction the input does not have."""
    assert maths.bar_width(0, 100, 400) == 0.0


def test_bar_width_is_signless():
    assert maths.bar_width(-50, 100, 400) == maths.bar_width(50, 100, 400)


def test_a_group_of_zeros_does_not_divide_by_zero():
    assert maths.bar_width(0, 0, 400) == 0.0
    assert maths.share_of_total([0, 0]) == [0.0, 0.0]


@pytest.mark.parametrize("span", [0, -1])
def test_a_chart_with_no_room_is_refused(span):
    with pytest.raises(ValueError):
        maths.bar_width(1, 10, span)


def test_shares_use_absolute_values_and_sum_to_one():
    shares = maths.share_of_total([600, -200, 200])
    assert sum(shares) == pytest.approx(1.0)
    assert shares[0] == pytest.approx(0.6)
    assert all(share >= 0 for share in shares)


def test_absent_numbers_are_written_as_words_not_zeros():
    assert maths.percent(None) == "unavailable"
    assert maths.multiple(None) == "unavailable"
    assert maths.percent(0.298) == "29.8%"
    assert maths.multiple(1.175) == "1.175x"


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_a_nonfinite_display_value_is_refused(value):
    with pytest.raises(ValueError):
        maths.percent(value)
    with pytest.raises(ValueError):
        maths.multiple(value)


def test_extremes_of_an_empty_group_still_draw_an_axis():
    assert maths.extremes([]) == (0.0, 0.0)
    assert maths.extremes([-2, 5, 1]) == (-2, 5)


def test_signed_counts_separate_long_short_and_flat():
    counts = maths.signed_counts([600, -200, 0, 5, -1])
    assert counts == {"long": 2, "short": 2, "flat": 1}
    assert sum(counts.values()) == 5
