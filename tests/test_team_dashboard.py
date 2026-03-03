from unittest.mock import MagicMock, patch

import streamlit as st

from modes import team_dashboard


def test_init_team_dashboard_state_sets_expected_defaults():
    st.session_state.clear()

    team_dashboard.init_team_dashboard_state()

    assert st.session_state["team_dashboard_view"] == "Team"
    assert st.session_state["selected_team"] is None
    assert st.session_state["selected_member"] is None
    assert st.session_state["team_filter_applied"] is False
    assert st.session_state["batch_members_list"] == []


def test_render_header_with_view_selector_updates_state_from_radio():
    st.session_state.clear()
    team_dashboard.init_team_dashboard_state()

    with patch("modes.team_dashboard.st.radio", return_value="Member"):
        team_dashboard.render_header_with_view_selector()

    assert st.session_state["team_dashboard_view"] == "Member"


def test_render_team_dashboard_shows_error_when_no_teams():
    cfg = MagicMock()
    cfg.get_all_teams.return_value = []

    with patch("modes.team_dashboard.get_team_config", return_value=cfg):
        with patch("modes.team_dashboard.st.error") as mock_error:
            team_dashboard.render_team_dashboard(client=MagicMock(), csv_path="teams.csv")

    mock_error.assert_called_once()


def test_render_team_dashboard_routes_to_team_view():
    st.session_state.clear()
    st.session_state["team_dashboard_view"] = "Team"

    cfg = MagicMock()
    cfg.get_all_teams.return_value = ["alpha"]

    with patch("modes.team_dashboard.get_team_config", return_value=cfg):
        with patch("modes.team_dashboard.render_header_with_view_selector"):
            with patch("modes.team_dashboard.render_add_team_member_form"):
                with patch("modes.team_dashboard.st.selectbox", return_value="alpha"):
                    with patch("modes.team_dashboard.render_team_view") as mock_team_view:
                        with patch("modes.team_dashboard.render_member_view") as mock_member_view:
                            team_dashboard.render_team_dashboard(MagicMock(), "teams.csv")

    mock_team_view.assert_called_once()
    mock_member_view.assert_not_called()


def test_render_team_dashboard_routes_to_member_view():
    st.session_state.clear()
    st.session_state["team_dashboard_view"] = "Member"

    cfg = MagicMock()
    cfg.get_all_teams.return_value = ["alpha"]

    with patch("modes.team_dashboard.get_team_config", return_value=cfg):
        with patch("modes.team_dashboard.render_header_with_view_selector"):
            with patch("modes.team_dashboard.render_add_team_member_form"):
                with patch("modes.team_dashboard.render_member_view") as mock_member_view:
                    team_dashboard.render_team_dashboard(MagicMock(), "teams.csv")

    mock_member_view.assert_called_once()
