"""
Team Analytics - Cache-safe API calls for team-level statistics.

Provides aggregated statistics for teams with proper caching to prevent
duplicate API calls. All functions use st.cache_data with team_id as key.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

import streamlit as st

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


@st.cache_data(show_spinner=False)
def get_team_commits(
    _client, team_id: str, team_members: List[str], user_info_list: List[Dict[str, Any]]
) -> Tuple[List[Dict], Dict[str, int], Dict[str, int]]:
    """
    Fetch and aggregate commits for all team members.

    Args:
        _client: GitLab client (not hashed for caching)
        team_id: Team identifier (for cache key)
        team_members: List of usernames in team
        user_info_list: List of user info dicts {id, username, ...}

    Returns:
        Tuple of (all_commits_list, member_commit_counts, stats_dict)
    """
    from gitlab_utils import commits, projects

    all_commits = []
    member_counts = {}

    for user_info in user_info_list:
        # Use the original CSV username as key so dashboard lookups match
        username = user_info.get("csv_username") or user_info.get("username")
        try:
            user_id = user_info.get("id")
            api_username = user_info.get("username")

            # Get user's projects
            proj_data = projects.get_user_projects(_client, user_id, api_username)
            all_projs = proj_data.get("all", [])

            # Get commits for all projects
            user_commits, commit_counts, _ = commits.get_user_commits(_client, user_info, all_projs)

            # Tag each commit with the team member username
            for c in user_commits:
                c["_team_member"] = username

            all_commits.extend(user_commits)
            member_counts[username] = len(user_commits)
        except Exception:
            member_counts[username] = 0
            continue

    # Calculate stats
    stats = {
        "total": len(all_commits),
        "morning_commits": len([c for c in all_commits if c.get("slot", "").lower() == "morning"]),
        "afternoon_commits": len(
            [c for c in all_commits if c.get("slot", "").lower() == "afternoon"]
        ),
        "other_commits": len([c for c in all_commits if c.get("slot", "").lower() == "other"]),
    }

    return all_commits, member_counts, stats


@st.cache_data(show_spinner=False)
def get_team_merge_requests(
    _client, team_id: str, user_info_list: List[Dict[str, Any]]
) -> Tuple[List[Dict], Dict[str, int], Dict[str, int]]:
    """
    Fetch and aggregate merge requests for all team members.

    Args:
        _client: GitLab client (not hashed for caching)
        team_id: Team identifier (for cache key)
        user_info_list: List of user info dicts

    Returns:
        Tuple of (all_mrs_list, member_mr_counts, stats_dict)
    """
    from gitlab_utils import merge_requests

    all_mrs = []
    member_counts = {}

    for user_info in user_info_list:
        # Use the original CSV username as key so dashboard lookups match
        username = user_info.get("csv_username") or user_info.get("username")
        try:
            user_id = user_info.get("id")

            user_mrs, _ = merge_requests.get_user_mrs(_client, user_id)

            # Tag each MR with the team member username
            for m in user_mrs:
                m["_team_member"] = username

            all_mrs.extend(user_mrs)
            member_counts[username] = len(user_mrs)
        except Exception:
            member_counts[username] = 0
            continue

    # Calculate stats
    stats = {
        "total": len(all_mrs),
        "merged": len([m for m in all_mrs if m.get("state", "").lower() == "merged"]),
        "opened": len([m for m in all_mrs if m.get("state", "").lower() == "opened"]),
        "closed": len([m for m in all_mrs if m.get("state", "").lower() == "closed"]),
    }

    return all_mrs, member_counts, stats


@st.cache_data(show_spinner=False)
def get_team_issues(
    _client, team_id: str, user_info_list: List[Dict[str, Any]]
) -> Tuple[List[Dict], Dict[str, int], Dict[str, int]]:
    """
    Fetch and aggregate issues for all team members.

    Args:
        _client: GitLab client (not hashed for caching)
        team_id: Team identifier (for cache key)
        user_info_list: List of user info dicts

    Returns:
        Tuple of (all_issues_list, member_issue_counts, stats_dict)
    """
    from gitlab_utils import issues

    all_issues = []
    member_counts = {}

    for user_info in user_info_list:
        # Use the original CSV username as key so dashboard lookups match
        username = user_info.get("csv_username") or user_info.get("username")
        try:
            user_id = user_info.get("id")

            user_issues, _ = issues.get_user_issues(_client, user_id)

            # Tag each issue with the team member username
            for iss in user_issues:
                iss["_team_member"] = username

            all_issues.extend(user_issues)
            member_counts[username] = len(user_issues)
        except Exception:
            member_counts[username] = 0
            continue

    # Calculate stats
    stats = {
        "total": len(all_issues),
        "opened": len([i for i in all_issues if i.get("state", "").lower() == "opened"]),
        "closed": len([i for i in all_issues if i.get("state", "").lower() == "closed"]),
    }

    return all_issues, member_counts, stats


@st.cache_data(show_spinner=False)
def get_team_projects(
    _client, team_id: str, user_info_list: List[Dict[str, Any]]
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Fetch and aggregate projects for all team members.

    Args:
        _client: GitLab client (not hashed for caching)
        team_id: Team identifier (for cache key)
        user_info_list: List of user info dicts

    Returns:
        Tuple of (all_projects_list, member_project_counts)
    """
    from gitlab_utils import projects

    all_projects = []
    member_counts = {}
    seen_project_ids = set()

    for user_info in user_info_list:
        # Use the original CSV username as key so dashboard lookups match
        username = user_info.get("csv_username") or user_info.get("username")
        try:
            user_id = user_info.get("id")
            api_username = user_info.get("username")

            proj_data = projects.get_user_projects(_client, user_id, api_username)
            user_proj_ids = set()

            for proj in proj_data.get("all", []):
                proj_id = proj.get("id")
                if proj_id not in seen_project_ids:
                    all_projects.append(proj)
                    seen_project_ids.add(proj_id)
                user_proj_ids.add(proj_id)

            member_counts[username] = len(user_proj_ids)
        except Exception:
            member_counts[username] = 0
            continue

    return all_projects, member_counts


@st.cache_data(show_spinner=False)
def get_team_groups(
    _client, team_id: str, user_info_list: List[Dict[str, Any]]
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Fetch and aggregate groups for all team members.

    Args:
        _client: GitLab client (not hashed for caching)
        team_id: Team identifier (for cache key)
        user_info_list: List of user info dicts

    Returns:
        Tuple of (all_groups_list, member_group_counts)
    """
    from gitlab_utils import groups

    all_groups = []
    member_counts = {}
    seen_group_ids = set()

    for user_info in user_info_list:
        # Use the original CSV username as key so dashboard lookups match
        username = user_info.get("csv_username") or user_info.get("username")
        try:
            user_id = user_info.get("id")

            user_groups = groups.get_user_groups(_client, user_id)
            user_group_ids = set()

            for grp in user_groups or []:
                grp_id = grp.get("id")
                if grp_id not in seen_group_ids:
                    all_groups.append(grp)
                    seen_group_ids.add(grp_id)
                user_group_ids.add(grp_id)

            member_counts[username] = len(user_group_ids)
        except Exception:
            member_counts[username] = 0
            continue

    return all_groups, member_counts


def get_user_info_from_users(client, usernames: List[str]) -> List[Dict[str, Any]]:
    """
    Get user info for multiple usernames.

    Args:
        client: GitLab client
        usernames: List of usernames

    Returns:
        List of user info dicts (each dict includes 'csv_username' key
        preserving the original CSV username for reliable lookups)
    """
    from gitlab_utils import users

    user_info_list = []
    for username in usernames:
        try:
            user_info = users.get_user_by_username(client, username)
            if user_info:
                # Preserve the original CSV username so analytics functions
                # can use it as the key (GitLab API may return different case)
                user_info["csv_username"] = username
                user_info_list.append(user_info)
        except Exception:
            continue

    return user_info_list


def filter_data_by_date(
    data: List[Dict[str, Any]],
    start_date: date,
    end_date: date,
    date_field: str = "created_at",
) -> List[Dict[str, Any]]:
    """
    Filter data by date range.

    Args:
        data: List of data dicts
        start_date: Start date
        end_date: End date
        date_field: Field name containing date

    Returns:
        Filtered list
    """
    from user_profile.profile_utils import parse_gitlab_datetime

    if not data or not start_date or not end_date:
        return data

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=LOCAL_TZ)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=LOCAL_TZ)

    filtered = []
    for item in data:
        try:
            date_str = item.get(date_field) or item.get("date")
            if not date_str:
                continue

            created_at = parse_gitlab_datetime(date_str)
            if created_at and start_dt <= created_at <= end_dt:
                filtered.append(item)
        except Exception:
            continue

    return filtered


def calculate_team_stats(
    commits_list: List[Dict],
    mrs_list: List[Dict],
    issues_list: List[Dict],
    projects_list: List[Dict],
    groups_list: List[Dict],
) -> Dict[str, int]:
    """
    Calculate team statistics summary.

    Args:
        commits_list: List of commits
        mrs_list: List of MRs
        issues_list: List of issues
        projects_list: List of projects
        groups_list: List of groups

    Returns:
        Dict with stats
    """
    return {
        "total_commits": len(commits_list),
        "morning_commits": len([c for c in commits_list if c.get("slot", "").lower() == "morning"]),
        "afternoon_commits": len(
            [c for c in commits_list if c.get("slot", "").lower() == "afternoon"]
        ),
        "other_commits": len([c for c in commits_list if c.get("slot", "").lower() == "other"]),
        "total_mrs": len(mrs_list),
        "merged_mrs": len([m for m in mrs_list if m.get("state", "").lower() == "merged"]),
        "open_mrs": len([m for m in mrs_list if m.get("state", "").lower() == "opened"]),
        "total_issues": len(issues_list),
        "open_issues": len([i for i in issues_list if i.get("state", "").lower() == "opened"]),
        "total_projects": len(projects_list),
        "total_groups": len(groups_list),
    }
