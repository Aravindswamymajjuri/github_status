from unittest.mock import MagicMock, patch

from user_profile import profile_ui


def test_profile_ui_handles_api_failures_without_crashing():
    users_api = MagicMock()
    users_api.get_user_groups.side_effect = RuntimeError("groups failed")
    users_api.get_user_projects.side_effect = RuntimeError("projects failed")
    users_api.get_user_commits.side_effect = RuntimeError("commits failed")
    users_api.get_user_issues.side_effect = RuntimeError("issues failed")
    users_api.get_user_merge_requests.side_effect = RuntimeError("mrs failed")

    client = MagicMock()
    client.users = users_api
    user_info = {"id": 1, "name": "Alice", "username": "alice", "web_url": "https://gitlab.com/alice"}

    with patch("user_profile.profile_ui.st.warning") as mock_warning:
        profile_ui.render_user_profile(client, user_info)

    assert mock_warning.call_count >= 2
