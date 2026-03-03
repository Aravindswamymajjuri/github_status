from unittest.mock import MagicMock, patch

from gitlab_utils import batch



@patch("gitlab_utils.users.get_user_by_username")
@patch("gitlab_utils.projects.get_user_projects")
@patch("gitlab_utils.commits.get_user_commits")
@patch("gitlab_utils.groups.get_user_groups")
@patch("gitlab_utils.merge_requests.get_user_mrs")
@patch("gitlab_utils.issues.get_user_issues")
def test_process_single_user_success(
    mock_issues,
    mock_mrs,
    mock_groups,
    mock_commits,
    mock_projects,
    mock_users,
):
    client = MagicMock()
    username = "testuser"
    user_id = 123

    mock_users.return_value = {"id": user_id, "username": username, "name": "Test User"}
    mock_projects.return_value = {
        "personal": [{"id": 1}],
        "contributed": [{"id": 2}],
        "all": [{"id": 1}, {"id": 2}],
    }
    mock_commits.return_value = ([], {1: 10, 2: 5}, {"total": 15})
    mock_groups.return_value = []
    mock_mrs.return_value = ([], {"total": 0})
    mock_issues.return_value = ([], {"total": 0})

    result = batch.process_single_user(client, username)

    assert result["status"] == "Success"
    assert result["username"] == username
    assert "projects" in result["data"]
    assert len(result["data"]["projects"]["personal"]) == 1
    assert len(result["data"]["projects"]["contributed"]) == 1


@patch("gitlab_utils.batch.process_single_user")
def test_process_batch_users_marks_worker_exceptions_as_crash(mock_process_single_user):
    client = MagicMock()

    def _result(_, username, date_range=None):
        del date_range
        if username == "bob":
            raise RuntimeError("boom")
        return {"username": username, "status": "Success", "data": {}}

    mock_process_single_user.side_effect = _result

    results = batch.process_batch_users(client, ["alice", "bob"])
    by_username = {item["username"]: item for item in results}

    assert by_username["alice"]["status"] == "Success"
    assert by_username["bob"]["status"] == "Crash"
    assert "boom" in by_username["bob"]["error"]
