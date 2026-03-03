from datetime import date
from unittest.mock import patch

from modes import team_analytics


@patch("gitlab_utils.users.get_user_by_username")
def test_get_user_info_from_users_preserves_original_csv_username(mock_get_user):
    mock_get_user.side_effect = [
        {"id": 1, "username": "alice"},
        None,
        RuntimeError("boom"),
    ]

    result = team_analytics.get_user_info_from_users(MagicClient(), ["AliceCSV", "missing", "error"])

    assert len(result) == 1
    assert result[0]["username"] == "alice"
    assert result[0]["csv_username"] == "AliceCSV"


def test_filter_data_by_date_uses_created_field_or_date_fallback():
    data = [
        {"created_at": "2026-01-01T08:00:00+05:30"},
        {"date": "2026-01-02T08:00:00+05:30"},
        {"created_at": "2026-01-10T08:00:00+05:30"},
    ]

    filtered = team_analytics.filter_data_by_date(data, date(2026, 1, 1), date(2026, 1, 2))

    assert len(filtered) == 2


def test_calculate_team_stats_counts_all_sections():
    stats = team_analytics.calculate_team_stats(
        commits_list=[{"slot": "Morning"}, {"slot": "Afternoon"}],
        mrs_list=[{"state": "merged"}, {"state": "opened"}],
        issues_list=[{"state": "opened"}],
        projects_list=[{"id": 1}, {"id": 2}],
        groups_list=[{"id": 3}],
    )

    assert stats == {
        "total_commits": 2,
        "morning_commits": 1,
        "afternoon_commits": 1,
        "other_commits": 0,
        "total_mrs": 2,
        "merged_mrs": 1,
        "open_mrs": 1,
        "total_issues": 1,
        "open_issues": 1,
        "total_projects": 2,
        "total_groups": 1,
    }


@patch("gitlab_utils.projects.get_user_projects")
def test_get_team_projects_deduplicates_across_members(mock_get_projects):
    mock_get_projects.side_effect = [
        {"all": [{"id": 1}, {"id": 2}]},
        {"all": [{"id": 2}, {"id": 3}]},
    ]
    user_info_list = [
        {"id": 11, "username": "u1", "csv_username": "csv1"},
        {"id": 12, "username": "u2", "csv_username": "csv2"},
    ]

    all_projects, member_counts = team_analytics.get_team_projects(MagicClient(), "team1", user_info_list)

    assert sorted(p["id"] for p in all_projects) == [1, 2, 3]
    assert member_counts == {"csv1": 2, "csv2": 2}


@patch("gitlab_utils.groups.get_user_groups")
def test_get_team_groups_handles_member_errors(mock_get_groups):
    mock_get_groups.side_effect = [
        [{"id": 100, "name": "A"}, {"id": 101, "name": "B"}],
        RuntimeError("boom"),
    ]
    user_info_list = [
        {"id": 1, "username": "u1", "csv_username": "csv1"},
        {"id": 2, "username": "u2", "csv_username": "csv2"},
    ]

    all_groups, member_counts = team_analytics.get_team_groups(MagicClient(), "team2", user_info_list)

    assert sorted(g["id"] for g in all_groups) == [100, 101]
    assert member_counts == {"csv1": 2, "csv2": 0}


@patch("gitlab_utils.projects.get_user_projects")
@patch("gitlab_utils.commits.get_user_commits")
def test_get_team_commits_tags_team_member_and_counts_slots(mock_get_commits, mock_get_projects):
    mock_get_projects.return_value = {"all": [{"id": 1}]}
    mock_get_commits.side_effect = [
        (
            [{"slot": "Morning", "message": "c1"}],
            {1: 1},
            {"total": 1, "morning_commits": 1, "afternoon_commits": 0},
        ),
        RuntimeError("boom"),
    ]
    user_info_list = [
        {"id": 10, "username": "alice", "csv_username": "AliceCSV"},
        {"id": 11, "username": "bob", "csv_username": "BobCSV"},
    ]

    commits_list, member_counts, stats = team_analytics.get_team_commits(
        MagicClient(),
        "team3",
        ["AliceCSV", "BobCSV"],
        user_info_list,
    )

    assert len(commits_list) == 1
    assert commits_list[0]["_team_member"] == "AliceCSV"
    assert member_counts == {"AliceCSV": 1, "BobCSV": 0}
    assert stats == {
        "total": 1,
        "morning_commits": 1,
        "afternoon_commits": 0,
        "other_commits": 0,
    }


@patch("gitlab_utils.merge_requests.get_user_mrs")
@patch("gitlab_utils.issues.get_user_issues")
def test_team_mr_and_issue_stats(mock_get_issues, mock_get_mrs):
    mock_get_mrs.return_value = (
        [{"state": "opened"}, {"state": "merged"}],
        {"total": 2, "opened": 1, "merged": 1, "closed": 0},
    )
    mock_get_issues.return_value = (
        [{"state": "opened"}, {"state": "closed"}],
        {"total": 2, "opened": 1, "closed": 1},
    )

    user_info_list = [{"id": 1, "username": "u1", "csv_username": "u1"}]
    mrs, mr_counts, mr_stats = team_analytics.get_team_merge_requests(MagicClient(), "team", user_info_list)
    issues, issue_counts, issue_stats = team_analytics.get_team_issues(MagicClient(), "team", user_info_list)

    assert len(mrs) == 2 and mr_counts["u1"] == 2 and mr_stats["total"] == 2
    assert len(issues) == 2 and issue_counts["u1"] == 2 and issue_stats["total"] == 2


class MagicClient:
    pass
