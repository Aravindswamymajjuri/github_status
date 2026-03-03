"""
Team Views - Analytics rendering for team and individual member dashboards.

Contains:
  render_date_filter      — date range filter widget
  render_team_view        — team-level stats, member contributions, pie chart
  render_member_view      — individual member stats, pie chart, activity history
  _show_pie_detail_dialog — @st.dialog popup for activity detail tables
"""

from datetime import date
from typing import Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modes.team_analytics import (
    filter_data_by_date,
    get_team_commits,
    get_team_groups,
    get_team_issues,
    get_team_merge_requests,
    get_team_projects,
    get_user_info_from_users,
)
from modes.team_config import TeamConfig
from modes.team_styles import (
    STAT_CARD_CSS,
    commits_card,
    issues_card,
    mr_card,
    simple_card,
)

# ── Shared pie-chart config ────────────────────────────────────────────────────
_PIE_LABELS = ["Commits", "Merge Requests", "Issues", "Projects", "Groups"]
_PIE_COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]


# ── Date filter ───────────────────────────────────────────────────────────────


def render_date_filter() -> Tuple[bool, Optional[date], Optional[date]]:
    """
    Render date filter UI.

    Returns:
        Tuple of (filter_applied, start_date, end_date)
    """
    st.markdown("---")
    st.subheader("🔍 Date Filter")

    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.team_filter_start,
            key="team_filter_start_input",
        )

    with col2:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.team_filter_end or start_date,
            key="team_filter_end_input",
        )

    with col3:
        if st.button("Apply Filter", use_container_width=True):
            if start_date > end_date:
                st.error("Start Date cannot be after End Date")
                return False, None, None
            st.session_state.team_filter_start = start_date
            st.session_state.team_filter_end = end_date
            st.session_state.team_filter_applied = True
            st.success(f"Filter applied: {start_date} to {end_date}")
            return True, start_date, end_date

    with col4:
        if st.button("Clear Filter", use_container_width=True):
            st.session_state.team_filter_start = None
            st.session_state.team_filter_end = None
            st.session_state.team_filter_applied = False
            st.success("Filter cleared")
            st.rerun()

    if st.session_state.team_filter_applied:
        return (
            True,
            st.session_state.team_filter_start,
            st.session_state.team_filter_end,
        )

    return False, None, None


# ── Shared pie chart helper ───────────────────────────────────────────────────


def _render_pie_chart(
    values: list,
    btn_key_prefix: str,
) -> None:
    """Render activity donut chart + detail buttons below it."""
    if sum(values) == 0:
        st.info("No activity data to visualize.")
        return

    fig = go.Figure(
        data=[
            go.Pie(
                labels=_PIE_LABELS,
                values=values,
                hole=0.4,
                marker={"colors": _PIE_COLORS},
                textinfo="label+percent",
                textposition="outside",
                hovertemplate=(
                    "<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        margin={"t": 30, "b": 30, "l": 10, "r": 10},
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption("Click a category below to view details")
    cols = st.columns(5)
    for idx, col in enumerate(cols):
        with col:
            label = _PIE_LABELS[idx]
            count = values[idx]
            if st.button(
                f"{label} ({count})",
                key=f"{btn_key_prefix}_{label}",
                use_container_width=True,
            ):
                st.session_state["_pie_dialog_section"] = label
                _show_pie_detail_dialog()


# ── Detail popup ──────────────────────────────────────────────────────────────


@st.dialog("Activity Details", width="large")
def _show_pie_detail_dialog() -> None:
    """Popup dialog showing detail tables for the selected activity section."""
    section = st.session_state.get("_pie_dialog_section")
    data_map = st.session_state.get("_pie_dialog_data", {})

    if not section or section not in data_map:
        st.warning("No data to display.")
        return

    items = data_map[section]
    limit = 200

    st.subheader(f"{section} ({len(items)})")

    if not items:
        st.info(f"No {section.lower()} found.")
    elif section == "Commits":
        rows = [
            {
                "ID": c.get("short_id", "—"),
                "Author": c.get("author_name", "—"),
                "Message": c.get("message") or "",
                "Project": c.get("project_name", "—"),
                "Date": c.get("date", "—"),
                "Time": c.get("time", "—"),
                "Slot": c.get("slot", "—"),
            }
            for c in items[:limit]
        ]
        df = pd.DataFrame(rows)
        df = _apply_column_filters(df, "commits")
        st.dataframe(df, use_container_width=True)

    elif section == "Merge Requests":
        rows = [
            {
                "Title": (m.get("title") or "—")[:80],
                "State": m.get("state", "—"),
                "Role": m.get("role", "—"),
                "Created": (m.get("created_at") or "—")[:10],
                "URL": m.get("web_url", "—"),
            }
            for m in items[:limit]
        ]
        df = pd.DataFrame(rows)
        df = _apply_column_filters(df, "mrs")
        st.dataframe(df, use_container_width=True)

    elif section == "Issues":
        rows = [
            {
                "Title": (i.get("title") or "—")[:80],
                "State": i.get("state", "—"),
                "Created": (i.get("created_at") or "—")[:10],
                "URL": i.get("web_url", "—"),
            }
            for i in items[:limit]
        ]
        df = pd.DataFrame(rows)
        df = _apply_column_filters(df, "issues")
        st.dataframe(df, use_container_width=True)

    elif section == "Projects":
        rows = [
            {
                "Name": p.get("name", "—"),
                "Path": p.get("path_with_namespace", "—"),
                "Visibility": p.get("visibility", "—"),
                "Stars": p.get("star_count", 0),
                "Forks": p.get("forks_count", 0),
                "Created": (p.get("created_at") or "—")[:10],
            }
            for p in items[:limit]
        ]
        df = pd.DataFrame(rows)
        df = _apply_column_filters(df, "projects")
        st.dataframe(df, use_container_width=True)

    elif section == "Groups":
        rows = [
            {
                "Name": g.get("name", "—"),
                "Path": g.get("full_path", g.get("path", "—")),
                "Visibility": g.get("visibility", "—"),
                "Description": (g.get("description") or "")[:60],
            }
            for g in items[:limit]
        ]
        df = pd.DataFrame(rows)
        df = _apply_column_filters(df, "groups")
        st.dataframe(df, use_container_width=True)

    if st.button("Close", use_container_width=True, key="pie_detail_close_btn"):
        st.rerun(scope="app")


def _apply_column_filters(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Render per-column filter widgets and return the filtered DataFrame."""
    if df.empty:
        return df

    filterable_cols = []
    for col in df.columns:
        nunique = df[col].nunique()
        # Only show filter for columns with a reasonable number of unique values
        if 2 <= nunique <= 50:
            filterable_cols.append(col)

    if not filterable_cols:
        return df

    with st.expander("🔍 Filters", expanded=False):
        cols_per_row = min(len(filterable_cols), 4)
        col_widgets = st.columns(cols_per_row)

        for idx, col_name in enumerate(filterable_cols):
            with col_widgets[idx % cols_per_row]:
                unique_vals = sorted(df[col_name].dropna().unique().tolist(), key=str)
                selected = st.multiselect(
                    col_name,
                    options=unique_vals,
                    default=unique_vals,
                    key=f"filter_{prefix}_{col_name}",
                )
                if selected and len(selected) < len(unique_vals):
                    df = df[df[col_name].isin(selected)]

    return df


# ── Team view ─────────────────────────────────────────────────────────────────


def render_team_view(client, team_config: TeamConfig, team_name: str) -> None:
    """Render team-level analytics: stat cards, member contributions, pie chart."""
    st.markdown("---")
    st.subheader(f"Team: {team_name}")

    team_members = team_config.get_team_members(team_name)
    member_count = len(team_members)

    st.write(f"**Members:** {member_count}")
    st.write(f"**Member List:** {', '.join(team_members)}")

    st.info(f"Loading data for {member_count} team members...")
    user_info_list = get_user_info_from_users(client, team_members)

    if not user_info_list:
        st.error("Could not fetch user information for team members")
        return

    st.success(f"Found {len(user_info_list)} members")

    filter_applied, start_date, end_date = render_date_filter()

    # ── Inject CSS ────────────────────────────────────────
    st.markdown(STAT_CARD_CSS, unsafe_allow_html=True)

    # ── Row 1: Commits | MRs | Issues ─────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        with st.spinner("Loading commits..."):
            all_commits, member_commit_counts, commit_stats = get_team_commits(
                client, team_name, team_members, user_info_list
            )
            if filter_applied and start_date and end_date:
                all_commits = filter_data_by_date(all_commits, start_date, end_date)
                commit_stats["total"] = len(all_commits)
                commit_stats["morning_commits"] = sum(
                    1 for c in all_commits if c.get("slot", "").lower() == "morning"
                )
                commit_stats["afternoon_commits"] = sum(
                    1 for c in all_commits if c.get("slot", "").lower() == "afternoon"
                )
                commit_stats["other_commits"] = sum(
                    1 for c in all_commits if c.get("slot", "").lower() == "other"
                )
            st.markdown(
                commits_card(
                    commit_stats.get("total", 0),
                    commit_stats.get("morning_commits", 0),
                    commit_stats.get("afternoon_commits", 0),
                    commit_stats.get("other_commits", 0),
                ),
                unsafe_allow_html=True,
            )

    with col2:
        with st.spinner("Loading MRs..."):
            all_mrs, member_mr_counts, mr_stats = get_team_merge_requests(
                client, team_name, user_info_list
            )
            if filter_applied and start_date and end_date:
                all_mrs = filter_data_by_date(all_mrs, start_date, end_date)
                mr_stats["total"] = len(all_mrs)
                mr_stats["merged"] = sum(
                    1 for m in all_mrs if m.get("state", "").lower() == "merged"
                )
                mr_stats["opened"] = sum(
                    1 for m in all_mrs if m.get("state", "").lower() == "opened"
                )
                mr_stats["closed"] = sum(
                    1 for m in all_mrs if m.get("state", "").lower() == "closed"
                )
            st.markdown(
                mr_card(
                    mr_stats.get("total", 0),
                    mr_stats.get("merged", 0),
                    mr_stats.get("opened", 0),
                    mr_stats.get("closed", 0),
                ),
                unsafe_allow_html=True,
            )

    with col3:
        with st.spinner("Loading issues..."):
            all_issues, member_issue_counts, issue_stats = get_team_issues(
                client, team_name, user_info_list
            )
            if filter_applied and start_date and end_date:
                all_issues = filter_data_by_date(all_issues, start_date, end_date)
                issue_stats["total"] = len(all_issues)
                issue_stats["opened"] = sum(
                    1 for i in all_issues if i.get("state", "").lower() == "opened"
                )
                issue_stats["closed"] = sum(
                    1 for i in all_issues if i.get("state", "").lower() == "closed"
                )
            st.markdown(
                issues_card(
                    issue_stats.get("total", 0),
                    issue_stats.get("opened", 0),
                    issue_stats.get("closed", 0),
                ),
                unsafe_allow_html=True,
            )

    # ── Row 2: Projects | Groups ───────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        with st.spinner("Loading projects..."):
            all_projects, member_project_counts = get_team_projects(
                client, team_name, user_info_list
            )
            st.markdown(
                simple_card("Projects", len(all_projects)),
                unsafe_allow_html=True,
            )

    with col2:
        with st.spinner("Loading groups..."):
            all_groups, member_group_counts = get_team_groups(client, team_name, user_info_list)
            st.markdown(
                simple_card("Groups", len(all_groups)),
                unsafe_allow_html=True,
            )

    # ── Member contributions table ─────────────────────────
    st.markdown("---")
    st.subheader("Member Contributions")

    # Recompute per-member counts from filtered data when filter is active
    if filter_applied and start_date and end_date:
        member_commit_counts = {}
        for c in all_commits:
            u = c.get("_team_member", "")
            member_commit_counts[u] = member_commit_counts.get(u, 0) + 1

        member_mr_counts = {}
        for m in all_mrs:
            u = m.get("_team_member", "")
            member_mr_counts[u] = member_mr_counts.get(u, 0) + 1

        member_issue_counts = {}
        for i in all_issues:
            u = i.get("_team_member", "")
            member_issue_counts[u] = member_issue_counts.get(u, 0) + 1

    member_data = [
        {
            "Username": u,
            "Commits": member_commit_counts.get(u, 0),
            "MRs": member_mr_counts.get(u, 0),
            "Issues": member_issue_counts.get(u, 0),
            "Projects": member_project_counts.get(u, 0),
            "Groups": member_group_counts.get(u, 0),
        }
        for u in team_members
    ]

    selection = st.selectbox(
        "Show contributions for:",
        options=["All"] + [r["Username"] for r in member_data],
        index=0,
        key="member_contrib_filter",
    )
    if selection != "All":
        member_data = [r for r in member_data if r["Username"] == selection]

    st.dataframe(pd.DataFrame(member_data), use_container_width=True)

    # ── Pie chart ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("Team Activity Distribution")

    pie_values = [
        commit_stats.get("total", 0),
        mr_stats.get("total", 0),
        issue_stats.get("total", 0),
        len(all_projects),
        len(all_groups),
    ]

    st.session_state["_pie_dialog_data"] = {
        "Commits": all_commits,
        "Merge Requests": all_mrs,
        "Issues": all_issues,
        "Projects": all_projects,
        "Groups": all_groups,
    }

    _render_pie_chart(pie_values, btn_key_prefix="team_pie_btn")


# ── Member view ───────────────────────────────────────────────────────────────


def _select_member(team_config: TeamConfig) -> str | None:
    """Return selected member username or None when unavailable."""
    all_members = team_config.get_all_members_as_flat_list()
    if not all_members:
        st.error("No members found in team configuration")
        return None
    selected_member = st.selectbox(
        "Select Team Member",
        options=all_members,
        key="member_selector",
    )
    return selected_member or None


def _apply_member_commit_filters(
    user_commits: list[dict],
    commit_stats: dict,
    filter_applied: bool,
    start_date: date | None,
    end_date: date | None,
) -> tuple[list[dict], dict]:
    """Apply date filter and recompute commit summary stats."""
    if not (filter_applied and start_date and end_date):
        return user_commits, commit_stats

    filtered_commits = filter_data_by_date(user_commits, start_date, end_date)
    filtered_stats = dict(commit_stats)
    filtered_stats["total"] = len(filtered_commits)
    filtered_stats["morning_commits"] = sum(
        1 for c in filtered_commits if c.get("slot", "").lower() == "morning"
    )
    filtered_stats["afternoon_commits"] = sum(
        1 for c in filtered_commits if c.get("slot", "").lower() == "afternoon"
    )
    filtered_stats["other_commits"] = sum(
        1 for c in filtered_commits if c.get("slot", "").lower() == "other"
    )
    return filtered_commits, filtered_stats


def _apply_member_state_filters(
    items: list[dict],
    stats: dict,
    filter_applied: bool,
    start_date: date | None,
    end_date: date | None,
    state_mapping: dict[str, str],
) -> tuple[list[dict], dict]:
    """Apply date filter and recompute state-based counters."""
    if not (filter_applied and start_date and end_date):
        return items, stats

    filtered_items = filter_data_by_date(items, start_date, end_date)
    filtered_stats = dict(stats)
    filtered_stats["total"] = len(filtered_items)
    for key, state_name in state_mapping.items():
        filtered_stats[key] = sum(
            1 for item in filtered_items if item.get("state", "").lower() == state_name
        )
    return filtered_items, filtered_stats


def _fetch_member_analytics(
    client,
    selected_member: str,
    filter_applied: bool,
    start_date: date | None,
    end_date: date | None,
) -> dict | None:
    """Fetch analytics for a member and apply optional date filter."""
    from gitlab_utils import (  # noqa: PLC0415
        commits,
        groups,
        issues,
        merge_requests,
        projects,
        users,
    )

    user_info = users.get_user_by_username(client, selected_member)
    if not user_info:
        st.error(f"Could not fetch user information for {selected_member}")
        return None

    user_id = user_info.get("id")
    proj_data = projects.get_user_projects(client, user_id, selected_member)
    all_projs = proj_data.get("all", [])

    user_commits, _, commit_stats = commits.get_user_commits(client, user_info, all_projs)
    user_commits, commit_stats = _apply_member_commit_filters(
        user_commits, commit_stats, filter_applied, start_date, end_date
    )

    user_mrs, mr_stats = merge_requests.get_user_mrs(client, user_id)
    user_mrs, mr_stats = _apply_member_state_filters(
        user_mrs,
        mr_stats,
        filter_applied,
        start_date,
        end_date,
        {"merged": "merged", "opened": "opened", "closed": "closed"},
    )

    user_issues, issue_stats = issues.get_user_issues(client, user_id)
    user_issues, issue_stats = _apply_member_state_filters(
        user_issues,
        issue_stats,
        filter_applied,
        start_date,
        end_date,
        {"opened": "opened", "closed": "closed"},
    )

    return {
        "commits": user_commits,
        "commit_stats": commit_stats,
        "mrs": user_mrs,
        "mr_stats": mr_stats,
        "issues": user_issues,
        "issue_stats": issue_stats,
        "projects": proj_data.get("all", []),
        "groups": groups.get_user_groups(client, user_id) or [],
    }


def _render_member_stat_cards(
    commit_stats: dict,
    mr_stats: dict,
    issue_stats: dict,
    user_projects: list[dict],
    user_groups: list[dict],
) -> None:
    """Render summary card rows for member activity."""
    st.markdown(STAT_CARD_CSS, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            commits_card(
                commit_stats.get("total", 0),
                commit_stats.get("morning_commits", 0),
                commit_stats.get("afternoon_commits", 0),
                commit_stats.get("other_commits", 0),
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            mr_card(
                mr_stats.get("total", 0),
                mr_stats.get("merged", 0),
                mr_stats.get("opened", 0),
                mr_stats.get("closed", 0),
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            issues_card(
                issue_stats.get("total", 0),
                issue_stats.get("opened", 0),
                issue_stats.get("closed", 0),
            ),
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(simple_card("Projects", len(user_projects)), unsafe_allow_html=True)
    with col2:
        st.markdown(simple_card("Groups", len(user_groups)), unsafe_allow_html=True)


def _render_member_pie(
    user_commits: list[dict],
    commit_stats: dict,
    user_mrs: list[dict],
    mr_stats: dict,
    user_issues: list[dict],
    issue_stats: dict,
    user_projects: list[dict],
    user_groups: list[dict],
) -> None:
    """Render member pie chart and register popup data map."""
    st.markdown("---")
    st.subheader("Activity Distribution")

    pie_values = [
        commit_stats.get("total", 0),
        mr_stats.get("total", 0),
        issue_stats.get("total", 0),
        len(user_projects),
        len(user_groups),
    ]

    st.session_state["_pie_dialog_data"] = {
        "Commits": user_commits,
        "Merge Requests": user_mrs,
        "Issues": user_issues,
        "Projects": user_projects,
        "Groups": user_groups,
    }
    _render_pie_chart(pie_values, btn_key_prefix="member_pie_btn")


def _render_member_commits_history(user_commits: list[dict]) -> None:
    """Render commits history table."""
    if not user_commits:
        st.info("No commits found.")
        return

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "ID": c.get("short_id", "—"),
                    "Date": c.get("date", "—"),
                    "Time": c.get("time", "—"),
                    "Slot": c.get("slot", "—"),
                    "Message": c.get("message") or "",
                    "Project": c.get("project_name", "—"),
                }
                for c in user_commits[:100]
            ]
        ),
        use_container_width=True,
    )


def _render_member_mr_history(user_mrs: list[dict]) -> None:
    """Render merge request history table."""
    if not user_mrs:
        st.info("No merge requests found.")
        return

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Title": (m.get("title") or "—")[:80],
                    "State": m.get("state", "—"),
                    "Role": m.get("role", "—"),
                    "Created": (m.get("created_at") or "—")[:10],
                    "URL": m.get("web_url", "—"),
                }
                for m in user_mrs[:100]
            ]
        ),
        use_container_width=True,
    )


def _render_member_issue_history(user_issues: list[dict]) -> None:
    """Render issue history table."""
    if not user_issues:
        st.info("No issues found.")
        return

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Title": (i.get("title") or "—")[:80],
                    "State": i.get("state", "—"),
                    "Created": (i.get("created_at") or "—")[:10],
                    "URL": i.get("web_url", "—"),
                }
                for i in user_issues[:100]
            ]
        ),
        use_container_width=True,
    )


def _render_member_history(
    user_commits: list[dict], user_mrs: list[dict], user_issues: list[dict]
) -> None:
    """Render tabbed history section for commits, merge requests, and issues."""
    st.markdown("---")
    st.subheader("Recent Activity History")

    history_tab = st.radio(
        "View history for:",
        ["Commits", "Merge Requests", "Issues"],
        horizontal=True,
        key="member_history_tab",
    )
    if history_tab == "Commits":
        _render_member_commits_history(user_commits)
        return
    if history_tab == "Merge Requests":
        _render_member_mr_history(user_mrs)
        return
    _render_member_issue_history(user_issues)


def render_member_view(client, team_config: TeamConfig) -> None:
    """Render individual member analytics: stat cards, pie chart, history."""
    selected_member = _select_member(team_config)
    if not selected_member:
        return

    member_teams = team_config.get_teams_for_member(selected_member)
    st.info(f"Member of: {', '.join(member_teams)}")
    filter_applied, start_date, end_date = render_date_filter()

    st.markdown("---")
    st.subheader(f"{selected_member} — Individual Analytics")

    with st.spinner(f"Loading data for {selected_member}..."):
        member_data = _fetch_member_analytics(
            client, selected_member, filter_applied, start_date, end_date
        )

    if not member_data:
        return

    _render_member_stat_cards(
        member_data["commit_stats"],
        member_data["mr_stats"],
        member_data["issue_stats"],
        member_data["projects"],
        member_data["groups"],
    )
    _render_member_pie(
        member_data["commits"],
        member_data["commit_stats"],
        member_data["mrs"],
        member_data["mr_stats"],
        member_data["issues"],
        member_data["issue_stats"],
        member_data["projects"],
        member_data["groups"],
    )
    _render_member_history(
        member_data["commits"],
        member_data["mrs"],
        member_data["issues"],
    )
