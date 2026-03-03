from datetime import datetime, timedelta, timezone

from user_profile import profile_utils

IST = timezone(timedelta(hours=5, minutes=30))


def test_parse_gitlab_datetime_handles_z_and_invalid_values():
    parsed = profile_utils.parse_gitlab_datetime("2026-01-01T00:00:00Z")

    assert parsed is not None
    assert parsed.tzinfo is not None
    assert profile_utils.parse_gitlab_datetime("not-a-date") is None
    assert profile_utils.parse_gitlab_datetime(None) is None


def test_classify_time_slot_boundaries():
    assert profile_utils.classify_time_slot("2026-01-01T04:00:00Z") == "Morning"
    assert profile_utils.classify_time_slot("2026-01-01T08:30:00Z") == "Afternoon"
    assert profile_utils.classify_time_slot("2026-01-01T11:31:00Z") == "Other"


def test_process_commits_filters_invalid_and_formats_fields():
    commits = [
        {
            "created_at": "2026-01-01T04:00:00Z",
            "project_scope": "Personal",
            "project_name": "P1",
            "title": "First",
        },
        {
            "created_at": "invalid",
            "project_scope": "Contributed",
            "project_name": "P2",
            "message": "fallback subject\nbody",
        },
    ]

    processed = profile_utils.process_commits(commits)

    assert len(processed) == 1
    assert processed[0]["project"] == "P1"
    assert processed[0]["slot"] == "Morning"


def test_process_groups_and_split_projects():
    groups = [{"name": "Team", "full_path": "grp/team", "visibility": "private"}]
    processed_groups = profile_utils.process_groups(groups)

    assert processed_groups == [
        {"name": "Team", "path": "grp/team", "visibility": "private", "web_url": "-"}
    ]

    projects = [
        {"namespace": {"full_path": "alice"}, "creator_id": 2, "id": 1},
        {"namespace": {"full_path": "team"}, "creator_id": 9, "id": 2},
    ]
    personal, contributed = profile_utils.split_projects(projects, {"username": "alice", "id": 2})
    assert [p["id"] for p in personal] == [1]
    assert [p["id"] for p in contributed] == [2]


def test_filter_data_by_date_range_works_with_timezone_awareness():
    start = datetime(2026, 1, 1, 0, 0, tzinfo=IST)
    end = datetime(2026, 1, 1, 23, 59, tzinfo=IST)
    raw = [
        {"created_at": "2026-01-01T05:00:00+05:30"},
        {"created_at": "2026-01-02T05:00:00+05:30"},
        {"created_at": "bad"},
    ]

    filtered = profile_utils.filter_data_by_date_range(raw, start, end)
    assert filtered == [{"created_at": "2026-01-01T05:00:00+05:30"}]


def test_filter_processed_commits_and_items():
    start = datetime(2026, 1, 1, 0, 0, tzinfo=IST)
    end = datetime(2026, 1, 2, 23, 59, tzinfo=IST)

    commits = [
        {"date": "2026-01-01"},
        {"date": "2026-01-02"},
        {"date": "bad"},
    ]
    filtered_commits = profile_utils.filter_processed_commits(commits, start, end)
    assert filtered_commits == [{"date": "2026-01-01"}, {"date": "2026-01-02"}]

    items = [
        {"created_at": "2026-01-01T05:00:00+05:30"},
        {"created_at": "2026-01-05T05:00:00+05:30"},
    ]
    filtered_items = profile_utils.filter_processed_items(items, start, end)
    assert filtered_items == [{"created_at": "2026-01-01T05:00:00+05:30"}]


def test_calculate_filtered_metrics_counts_all_sections():
    commits = [{"slot": "Morning"}, {"slot": "Afternoon"}, {"slot": "Other"}]
    issues = [{"state": "opened"}, {"state": "closed"}, {"state": "opened"}]
    mrs = [{"state": "opened"}, {"state": "closed"}, {"state": "merged"}]

    metrics = profile_utils.calculate_filtered_metrics(commits, issues, mrs)

    assert metrics == {
        "total_commits": 3,
        "morning_commits": 1,
        "afternoon_commits": 1,
        "total_issues": 3,
        "issue_open": 2,
        "issue_closed": 1,
        "total_mrs": 3,
        "mr_open": 1,
        "mr_closed": 1,
        "mr_merged": 1,
    }
