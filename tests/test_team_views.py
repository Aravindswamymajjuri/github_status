from datetime import date
from unittest.mock import patch

import streamlit as st

from modes import team_views


def test_render_date_filter_apply_path_sets_session_values():
    st.session_state.clear()
    st.session_state["team_filter_start"] = None
    st.session_state["team_filter_end"] = None
    st.session_state["team_filter_applied"] = False

    with patch("modes.team_views.st.date_input", side_effect=[date(2026, 1, 1), date(2026, 1, 2)]):
        with patch("modes.team_views.st.button", side_effect=[True, False]):
            applied, start, end = team_views.render_date_filter()

    assert applied is True
    assert start == date(2026, 1, 1)
    assert end == date(2026, 1, 2)
    assert st.session_state["team_filter_applied"] is True


def test_render_date_filter_invalid_range_returns_false():
    st.session_state.clear()
    st.session_state["team_filter_start"] = None
    st.session_state["team_filter_end"] = None
    st.session_state["team_filter_applied"] = False

    with patch("modes.team_views.st.date_input", side_effect=[date(2026, 1, 3), date(2026, 1, 2)]):
        with patch("modes.team_views.st.button", side_effect=[True, False]):
            with patch("modes.team_views.st.error") as mock_error:
                applied, start, end = team_views.render_date_filter()

    assert applied is False
    assert start is None
    assert end is None
    mock_error.assert_called_once()


def test_render_pie_chart_handles_zero_values():
    with patch("modes.team_views.st.info") as mock_info:
        team_views._render_pie_chart([0, 0, 0, 0, 0], "pie")
    mock_info.assert_called_once()


def test_render_pie_chart_sets_selected_section_when_button_clicked():
    st.session_state.clear()

    with patch("modes.team_views.st.button", side_effect=[True, False, False, False, False]):
        with patch("modes.team_views._show_pie_detail_dialog") as mock_dialog:
            team_views._render_pie_chart([1, 2, 3, 4, 5], "pie")

    assert st.session_state["_pie_dialog_section"] == "Commits"
    mock_dialog.assert_called_once()


def test_show_pie_detail_dialog_warns_when_no_section():
    st.session_state.clear()
    st.session_state["_pie_dialog_section"] = None
    st.session_state["_pie_dialog_data"] = {}

    with patch("modes.team_views.st.warning") as mock_warning:
        team_views._show_pie_detail_dialog()

    mock_warning.assert_called_once()
