"""
Team Dashboard - Orchestration layer for team analytics.

Layout:
  team_styles.py   — CSS constants and HTML builder helpers
  team_views.py    — render_date_filter, render_team_view,
                     render_member_view, _show_pie_detail_dialog
  team_dashboard.py (this file) — session-state init, header,
                     team-management dialog, main entry point
"""

import streamlit as st

from modes.team_config import TeamConfig, get_team_config, reload_team_config
from modes.team_views import render_member_view, render_team_view

# ── Session state ─────────────────────────────────────────────────────────────


def init_team_dashboard_state() -> None:
    """Initialize session state keys for the team dashboard."""
    defaults = {
        "team_dashboard_view": "Team",
        "selected_team": None,
        "selected_member": None,
        "team_filter_start": None,
        "team_filter_end": None,
        "team_filter_applied": False,
        "batch_members_list": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Header ────────────────────────────────────────────────────────────────────


def render_header_with_view_selector() -> None:
    """Render the dashboard title and Team/Member view toggle."""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title("Team Analytics Dashboard")

    with col2:
        st.session_state.team_dashboard_view = st.radio(
            "View",
            options=["Team", "Member"],
            horizontal=True,
            key="view_selector",
        )


# ── Team management form + dialog ────────────────────────────────────────────


def render_add_team_member_form(team_config: TeamConfig, csv_path: str) -> None:
    """Button that opens the Manage Teams popup dialog."""
    st.markdown("---")

    if st.button(
        "Add / Manage Teams",
        use_container_width=True,
        key="open_team_dialog_btn",
        type="primary",
    ):
        _open_team_dialog(team_config, csv_path)


@st.dialog("Manage Teams", width="large")
def _open_team_dialog(team_config: TeamConfig, csv_path: str) -> None:
    """Native Streamlit popup dialog for adding and deleting teams/members."""
    team_name = _render_team_selection(team_config, csv_path)
    if not team_name:
        st.info("Select or create a team above to add members")
        return
    _render_member_addition_panel(team_config, team_name)


def _render_team_selection(team_config: TeamConfig, csv_path: str) -> str | None:
    """Render team chooser/create controls and return target team name."""
    choice = st.radio(
        "Choose an action",
        options=["Select Existing Team", "Create New Team"],
        horizontal=True,
        key="dlg_team_choice",
    )
    if choice == "Select Existing Team":
        return _render_existing_team_selector(team_config, csv_path)
    raw = st.text_input(
        "Enter New Team Name",
        placeholder="e.g., Backend Team, QA Team",
        key="dlg_new_team_input",
    )
    return raw.strip() if raw else None


def _render_existing_team_selector(team_config: TeamConfig, csv_path: str) -> str | None:
    """Render existing-team select/delete controls."""
    existing_teams = team_config.get_all_teams()
    if not existing_teams:
        st.warning("No teams available. Create a new team.")
        return None

    col_select, col_delete = st.columns([3, 1])
    with col_select:
        selected_team = st.selectbox(
            "Select a Team",
            options=existing_teams,
            key="dlg_existing_team_select",
        )
    with col_delete:
        st.write("")
        st.write("")
        _handle_delete_team(team_config, csv_path, selected_team)

    _render_existing_members(team_config, csv_path, selected_team)
    return selected_team or None


def _handle_delete_team(team_config: TeamConfig, csv_path: str, selected_team: str) -> None:
    """Delete selected team and reload configuration."""
    if not selected_team:
        return
    if st.button(
        "Delete Team",
        use_container_width=True,
        key="dlg_delete_team_btn",
        help="Remove this team from CSV",
    ):
        if team_config.remove_team(selected_team):
            st.success(f"Team '{selected_team}' deleted")
            reload_team_config(csv_path)
            st.rerun(scope="app")
        else:
            st.error(f"Failed to delete '{selected_team}'")


def _render_existing_members(team_config: TeamConfig, csv_path: str, selected_team: str) -> None:
    """Show current members of selected team with per-member remove action."""
    if not selected_team:
        return
    current_members = team_config.get_team_members(selected_team)
    if not current_members:
        return

    st.markdown("---")
    st.subheader(f"Current Members of **{selected_team}** ({len(current_members)})")
    for idx, member in enumerate(current_members):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"**{idx + 1}.** {member}")
        with c2:
            if st.button(
                "Remove",
                key=f"dlg_rm_existing_{idx}_{member}",
                use_container_width=True,
            ):
                if team_config.remove_team_member(selected_team, member):
                    reload_team_config(csv_path)
                    st.rerun(scope="app")
                else:
                    st.error(f"Failed to remove '{member}' from '{selected_team}'")


def _add_pending_member() -> None:
    """Append typed username to pending list if not empty/duplicate."""
    username = st.session_state.get("dlg_username_input", "").strip()
    if username and username not in st.session_state.batch_members_list:
        st.session_state.batch_members_list.append(username)
    st.session_state.dlg_username_input = ""


def _remove_pending_member(username: str) -> None:
    """Remove a username from pending list."""
    if username in st.session_state.batch_members_list:
        st.session_state.batch_members_list.remove(username)


def _render_member_input_controls() -> None:
    """Render input + add button for pending member list."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.text_input(
            "Enter Username",
            placeholder="GitLab username",
            key="dlg_username_input",
        )
    with col2:
        st.write("")
        st.write("")
        st.button(
            "Add",
            use_container_width=True,
            key="dlg_add_btn",
            on_click=_add_pending_member,
        )


def _render_pending_members() -> None:
    """Render staged usernames with remove buttons."""
    pending_members = st.session_state.batch_members_list
    if not pending_members:
        return
    st.markdown("---")
    st.write(f"**Members to add ({len(pending_members)}):**")
    for idx, username in enumerate(pending_members):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"**{idx + 1}.** {username}")
        with c2:
            st.button(
                "Remove",
                key=f"dlg_rm_{idx}_{username}",
                use_container_width=True,
                on_click=_remove_pending_member,
                args=(username,),
            )


def _save_pending_members(team_config: TeamConfig, team_name: str) -> None:
    """Persist pending members into selected team and save CSV."""
    added = 0
    skipped = 0
    for username in st.session_state.batch_members_list:
        if team_config.add_team_member(team_name, username):
            added += 1
        else:
            skipped += 1

    if team_config.save_to_csv():
        st.success(f"Saved {added} member(s) to CSV")
        if skipped:
            st.info(f"{skipped} already existed")
        st.session_state.batch_members_list = []
        st.rerun(scope="app")
    else:
        st.error("Failed to save CSV")


def _render_member_addition_panel(team_config: TeamConfig, team_name: str) -> None:
    """Render add-members UI for selected/new team."""
    st.markdown("---")
    st.subheader(f"Add Members to **{team_name}**")
    _render_member_input_controls()
    _render_pending_members()

    st.markdown("---")
    pending_count = len(st.session_state.batch_members_list)
    if st.button(
        f"Save {pending_count} Members",
        use_container_width=True,
        key="dlg_save_btn",
        type="primary",
        disabled=(pending_count == 0),
    ):
        _save_pending_members(team_config, team_name)


# ── Main entry point ──────────────────────────────────────────────────────────


def render_team_dashboard(client, csv_path: str) -> None:
    """
    Main team dashboard entry point.

    Args:
        client:   GitLab client instance
        csv_path: Path to team configuration CSV
    """
    init_team_dashboard_state()

    team_config = get_team_config(csv_path)

    if not team_config.get_all_teams():
        st.error(f"No teams loaded from {csv_path}")
        return

    render_header_with_view_selector()
    render_add_team_member_form(team_config, csv_path)

    if st.session_state.team_dashboard_view == "Team":
        selected_team = st.selectbox(
            "Select Team",
            options=team_config.get_all_teams(),
            key="team_selector",
        )
        if selected_team:
            render_team_view(client, team_config, selected_team)
    else:
        render_member_view(client, team_config)
