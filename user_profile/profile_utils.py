from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def parse_gitlab_datetime(timestamp):
    if not timestamp:
        return None
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(LOCAL_TZ)
    except Exception:
        return None


def classify_time_slot(timestamp):
    """
    Morning:   09:00 – 12:30
    Afternoon: 14:00 – 17:00
    Other:     All other times
    """
    dt = parse_gitlab_datetime(timestamp)
    if not dt:
        return None

    hour = dt.hour
    minute = dt.minute

    # Morning: 9:00 AM to 12:30 PM
    # 9, 10, 11 are fully in. 12 is in if minute <= 30.
    if (9 <= hour < 12) or (hour == 12 and minute <= 30):
        return "Morning"

    # Afternoon: 2:00 PM to 5:00 PM (14:00 - 17:00)
    # 14, 15, 16 are fully in.
    # 17:00 is on the edge; treat "until 5" as inclusive.
    # User said "2-5 pm". I'll assume 14:00:00 to 17:00:00 inclusive.
    if 14 <= hour <= 17:
        if hour == 17 and minute > 0:
            return "Other"
        return "Afternoon"

    return "Other"


def _format_date_time(timestamp):
    dt = parse_gitlab_datetime(timestamp)
    if not dt:
        return "-", "-"
    return dt.date().isoformat(), dt.strftime("%I:%M %p")


def process_commits(commits):
    processed = []
    for commit in commits or []:
        created_at = commit.get("created_at") or commit.get("committed_date")
        slot = classify_time_slot(created_at)
        if slot is None:
            continue

        date_str, time_str = _format_date_time(created_at)
        processed.append(
            {
                "project_type": commit.get("project_scope", "-"),
                "project": commit.get("project_name", "-"),
                "message": commit.get("title") or commit.get("message", "").split("\n")[0],
                "date": date_str,
                "time": time_str,
                "slot": slot,
            }
        )
    return processed


def process_groups(groups):
    rows = []
    for group in groups or []:
        rows.append(
            {
                "name": group.get("name", "-"),
                "path": group.get("full_path") or group.get("path", "-"),
                "visibility": group.get("visibility", "-"),
                "web_url": group.get("web_url", "-"),
            }
        )
    return rows


def split_projects(projects, user_info):
    personal = []
    contributed = []

    username = (user_info.get("username") or "").lower()
    user_id = user_info.get("id")

    for project in projects or []:
        namespace_path = (project.get("namespace", {}) or {}).get("full_path", "").lower()
        creator_id = project.get("creator_id")

        if namespace_path == username or creator_id == user_id:
            personal.append(project)
        else:
            contributed.append(project)

    return personal, contributed


def filter_data_by_date_range(
    data: List[Dict[str, Any]], start_date: Optional[datetime], end_date: Optional[datetime]
) -> List[Dict[str, Any]]:
    """
    Filter raw API data (commits, issues, MRs) by date range.

    Args:
        data: List of raw API objects with 'created_at' field
        start_date: Start date (inclusive), can be naive or timezone-aware
        end_date: End date (inclusive), can be naive or timezone-aware

    Returns:
        List of items where start_date <= created_at <= end_date
    """
    if not data or start_date is None or end_date is None:
        return data or []

    # Ensure dates are timezone-aware (assume local timezone if naive)
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=LOCAL_TZ)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=LOCAL_TZ)

    filtered = []
    for item in data:
        created_at = parse_gitlab_datetime(item.get("created_at"))
        if created_at is None:
            continue

        # Compare dates (inclusive on both ends)
        if start_date <= created_at <= end_date:
            filtered.append(item)

    return filtered


def filter_processed_commits(
    commits: List[Dict[str, Any]], start_date: Optional[datetime], end_date: Optional[datetime]
) -> List[Dict[str, Any]]:
    """
    Filter processed commits by date range based on the 'date' field.

    Args:
        commits: List of processed commit dictionaries with 'date' field
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Filtered list of commits
    """
    if not commits or start_date is None or end_date is None:
        return commits or []

    # Normalize to date comparison (no time component)
    start_date_only = start_date.date() if isinstance(start_date, datetime) else start_date
    end_date_only = end_date.date() if isinstance(end_date, datetime) else end_date

    filtered = []
    for commit in commits:
        try:
            commit_date = datetime.fromisoformat(commit.get("date")).date()
            if start_date_only <= commit_date <= end_date_only:
                filtered.append(commit)
        except (ValueError, TypeError):
            continue

    return filtered


def filter_processed_items(
    items: List[Dict[str, Any]], start_date: Optional[datetime], end_date: Optional[datetime]
) -> List[Dict[str, Any]]:
    """
    Filter processed items (issues, MRs) by date range based on 'created_at' field.

    Args:
        items: List of processed item dictionaries with 'created_at' field
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Filtered list of items
    """
    if not items or start_date is None or end_date is None:
        return items or []

    # Ensure dates are timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=LOCAL_TZ)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=LOCAL_TZ)

    filtered = []
    for item in items:
        created_at = parse_gitlab_datetime(item.get("created_at"))
        if created_at is None:
            continue

        if start_date <= created_at <= end_date:
            filtered.append(item)

    return filtered


def calculate_filtered_metrics(
    commits: List[Dict[str, Any]], issues: List[Dict[str, Any]], mrs: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Calculate metrics from filtered data.

    Args:
        commits: Filtered list of processed commits
        issues: Filtered list of processed issues
        mrs: Filtered list of processed merge requests

    Returns:
        Dictionary containing metrics
    """
    morning_commits = len([c for c in commits if (c.get("slot") or "").lower() == "morning"])
    afternoon_commits = len([c for c in commits if (c.get("slot") or "").lower() == "afternoon"])

    # Count MR and issue states
    mr_open = len([m for m in mrs if (m.get("state") or "").lower() == "opened"])
    mr_closed = len([m for m in mrs if (m.get("state") or "").lower() == "closed"])
    mr_merged = len([m for m in mrs if (m.get("state") or "").lower() == "merged"])

    issue_open = len([i for i in issues if (i.get("state") or "").lower() == "opened"])
    issue_closed = len([i for i in issues if (i.get("state") or "").lower() == "closed"])

    return {
        "total_commits": len(commits),
        "morning_commits": morning_commits,
        "afternoon_commits": afternoon_commits,
        "total_issues": len(issues),
        "issue_open": issue_open,
        "issue_closed": issue_closed,
        "total_mrs": len(mrs),
        "mr_open": mr_open,
        "mr_closed": mr_closed,
        "mr_merged": mr_merged,
    }
