from datetime import datetime, time, timezone

DATE_INPUT_FORMAT = "%Y-%m-%d"


class DateRangeValidationError(ValueError):
    """Raised when date range inputs are invalid."""


def _parse_date(flag_name, value):
    try:
        return datetime.strptime(value, DATE_INPUT_FORMAT).date()
    except ValueError as exc:
        raise DateRangeValidationError(
            f"Invalid value for {flag_name}: '{value}'. Expected format is YYYY-MM-DD."
        ) from exc


def parse_date_range(from_value=None, to_value=None, tz=timezone.utc):
    """
    Parse --from/--to values into timezone-aware inclusive day boundaries.
    Returns None if both values are omitted.
    """
    from_value = (from_value or "").strip() or None
    to_value = (to_value or "").strip() or None

    if from_value is None and to_value is None:
        return None

    if from_value and not to_value:
        raise DateRangeValidationError("Missing --to argument. Use --from and --to together.")
    if to_value and not from_value:
        raise DateRangeValidationError("Missing --from argument. Use --from and --to together.")

    from_date = _parse_date("--from", from_value)
    to_date = _parse_date("--to", to_value)

    start_dt = datetime.combine(from_date, time.min, tzinfo=tz)
    end_dt = datetime.combine(to_date, time.max, tzinfo=tz)

    if start_dt > end_dt:
        raise DateRangeValidationError("Invalid date range: --from must be on or before --to.")

    return start_dt, end_dt


def add_date_range_arguments(parser):
    """Add optional --from/--to YYYY-MM-DD arguments to a parser."""
    parser.add_argument(
        "--from",
        dest="from_date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive) in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="End date (inclusive) in YYYY-MM-DD format.",
    )
    return parser


def to_utc_iso(dt):
    """Convert a timezone-aware datetime to UTC ISO-8601 string."""
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware.")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def apply_range_params(base_params, date_range, start_key, end_key):
    """Add converted date range params into an API params dictionary."""
    params = dict(base_params or {})
    if not date_range:
        return params

    start_dt, end_dt = date_range
    params[start_key] = to_utc_iso(start_dt)
    params[end_key] = to_utc_iso(end_dt)
    return params
