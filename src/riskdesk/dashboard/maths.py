"""Display arithmetic for the dashboard, and nothing else.

Every function here is pure, takes numbers and returns numbers or strings.
No risk is calculated in this module or anywhere else in the dashboard: the
figures come from riskdesk.analytics through riskdesk.report, and these
helpers only decide how wide a bar is and how a number is written down.

That separation is the point. A dashboard that recomputed anything would
be a second implementation of the same measure, free to disagree with the
CLI and the MCP tools, and the disagreement would show up as two different
numbers in front of the same person.
"""
import math


def safe_ratio(numerator, denominator):
    """A ratio, or None when it is not defined.

    Returning None rather than zero matters: a leverage that cannot be
    computed because NAV is absent is not a leverage of zero, and printing
    zero would read as a book with no exposure.
    """
    if denominator in (0, None) or numerator is None:
        return None
    ratio = numerator / denominator
    return ratio if math.isfinite(ratio) else None


def bar_width(value, largest, span, minimum=1.0):
    """How wide a bar is, scaled against the largest in its group.

    The minimum keeps a tiny non-zero value visible, because a bar rounded
    away reads as an absent position rather than a small one. An exact zero
    gets no width from here; the caller decides how to draw nothing.
    """
    if span <= 0:
        raise ValueError("bar span must be positive")
    if value == 0:
        return 0.0
    largest = abs(largest) or abs(value)
    if largest == 0:
        return 0.0
    width = abs(value) / largest * span
    if not math.isfinite(width):
        raise ValueError("bar width is not finite")
    return max(width, minimum)


def share_of_total(values):
    """Each value's share of the total absolute value, largest first."""
    total = math.fsum(abs(v) for v in values)
    if total == 0:
        return [0.0 for _ in values]
    return [abs(v) / total for v in values]


def percent(fraction, places=1):
    """A fraction written as a percentage string, for display only."""
    if fraction is None:
        return "unavailable"
    if not math.isfinite(fraction):
        raise ValueError("percentage is not finite")
    return "{:.{}f}%".format(fraction * 100, places)


def multiple(ratio, places=4):
    """A ratio written as a multiple, or the word for its absence."""
    if ratio is None:
        return "unavailable"
    if not math.isfinite(ratio):
        raise ValueError("multiple is not finite")
    return "{:.{}g}x".format(ratio, places)


def extremes(values):
    """The most negative and most positive value, as a pair.

    Used to decide which side of a zero line a group needs. An empty group
    is (0.0, 0.0) so a caller can still draw an axis.
    """
    if not values:
        return 0.0, 0.0
    return min(values), max(values)


def signed_counts(values):
    """How many values are long, short and exactly flat.

    The dashboard prints this above the exposure ladder, because "two of
    six legs are short" is the sentence a reader wants before they read any
    bar at all.
    """
    long_count = sum(1 for v in values if v > 0)
    short_count = sum(1 for v in values if v < 0)
    return {"long": long_count, "short": short_count,
            "flat": len(values) - long_count - short_count}
