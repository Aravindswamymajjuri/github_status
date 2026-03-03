import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from gitlab_utils import users, projects, commits, groups, merge_requests, issues
from user_profile.profile_utils import parse_gitlab_datetime

LOCAL_TZ = ZoneInfo("Asia/Kolkata")

def render_user_profile(client, simple_user_info):
    """
    Renders the User Profile UI.
    """
    if not simple_user_info:
        st.error("User info not provided.")
        return

    user_id = simple_user_info.get("id")
    username = simple_user_info.get("username")
    name = simple_user_info.get("name")
    avatar_url = simple_user_info.get("avatar_url")
    web_url = simple_user_info.get("web_url")

    # Header
    col1, col2 = st.columns([1, 4])
    with col1:
        if avatar_url:
            st.image(avatar_url, width=100)
    with col2:
        st.markdown(f"### {name} (@{username})")
        st.markdown(f"**ID:** {user_id} | [GitLab Profile]({web_url})")

    # === Date Filter State Management ===
    if "show_date_filter" not in st.session_state:
        st.session_state.show_date_filter = False
    if "filter_start_date" not in st.session_state:
        st.session_state.filter_start_date = None
    if "filter_end_date" not in st.session_state:
        st.session_state.filter_end_date = None
    if "filter_applied" not in st.session_state:
        st.session_state.filter_applied = False
    
    # === Data Caching in Session State ===
    cache_key = f"user_data_{user_id}"
    if cache_key not in st.session_state:
        # Fetch Data ONCE and store in session state
        with st.spinner("Fetching comprehensive user data..."):
            # 1. Projects
            proj_data = projects.get_user_projects(client, user_id, username)

            # 2. Commits - Passing full simple_user_info
            all_projs = proj_data["all"]
            all_commits, commit_counts, commit_stats = commits.get_user_commits(client, simple_user_info, all_projs)

            verified_contributed = []
            for p in proj_data["contributed"]:
                 if commit_counts.get(p['id'], 0) > 0:
                     verified_contributed.append(p)

            personal_projects = proj_data["personal"]

            # 3. Groups
            user_groups = groups.get_user_groups(client, user_id)

            # 4. MRs
            user_mrs, mr_stats = merge_requests.get_user_mrs(client, user_id)

            # 5. Issues
            user_issues, issue_stats = issues.get_user_issues(client, user_id)
        
        # Store all data in session state
        st.session_state[cache_key] = {
            "proj_data": proj_data,
            "all_commits": all_commits,
            "commit_counts": commit_counts,
            "commit_stats": commit_stats,
            "verified_contributed": verified_contributed,
            "personal_projects": personal_projects,
            "user_groups": user_groups,
            "user_mrs": user_mrs,
            "mr_stats": mr_stats,
            "user_issues": user_issues,
            "issue_stats": issue_stats,
        }
    
    # Retrieve data from cache
    cached_data = st.session_state[cache_key]
    proj_data = cached_data["proj_data"]
    all_commits = cached_data["all_commits"].copy()
    commit_counts = cached_data["commit_counts"]
    commit_stats = cached_data["commit_stats"].copy()
    verified_contributed = cached_data["verified_contributed"]
    personal_projects = cached_data["personal_projects"]
    user_groups = cached_data["user_groups"]
    user_mrs = cached_data["user_mrs"].copy()
    mr_stats = cached_data["mr_stats"].copy()
    user_issues = cached_data["user_issues"].copy()
    issue_stats = cached_data["issue_stats"].copy()

    # === Date Filter UI ===
    st.markdown("---")
    st.subheader("🔍 Filters")
    filter_col1, filter_col2 = st.columns([1, 4])
    
    with filter_col1:
        if st.button("🗓️ Date Filter", use_container_width=True):
            st.session_state.show_date_filter = not st.session_state.show_date_filter
            st.session_state.filter_applied = False
    
    with filter_col2:
        if st.session_state.show_date_filter:
            with st.container(border=True):
                filter_sub_col1, filter_sub_col2, filter_sub_col3 = st.columns([2, 2, 1])
                
                with filter_sub_col1:
                    start_date = st.date_input(
                        "Start Date",
                        value=st.session_state.filter_start_date,
                        key="filter_start_input",
                    )
                
                with filter_sub_col2:
                    end_date = st.date_input(
                        "End Date",
                        value=st.session_state.filter_end_date if st.session_state.filter_end_date else start_date,
                        key="filter_end_input",
                    )
                
                with filter_sub_col3:
                    apply_filter = st.button("Apply Filter", use_container_width=True)
                
                if apply_filter:
                    # Validate date range
                    if start_date > end_date:
                        st.error("❌ Start Date cannot be greater than End Date")
                        st.session_state.filter_applied = False
                    else:
                        st.session_state.filter_start_date = start_date
                        st.session_state.filter_end_date = end_date
                        st.session_state.filter_applied = True
                        st.success(f"✅ Filter applied: {start_date} to {end_date}")

    # === Apply Date Filter to Data ===
    if st.session_state.filter_applied:
        start_date_obj = datetime.combine(st.session_state.filter_start_date, datetime.min.time()).replace(tzinfo=LOCAL_TZ)
        end_date_obj = datetime.combine(st.session_state.filter_end_date, datetime.max.time()).replace(tzinfo=LOCAL_TZ)
        
        # Filter commits
        filtered_commits = []
        for commit in all_commits:
            try:
                created_at = parse_gitlab_datetime(commit.get("created_at") or commit.get("date"))
                if created_at and start_date_obj <= created_at <= end_date_obj:
                    filtered_commits.append(commit)
            except:
                continue
        
        # Filter MRs
        filtered_mrs = []
        for mr in user_mrs:
            try:
                created_at = parse_gitlab_datetime(mr.get("created_at"))
                if created_at and start_date_obj <= created_at <= end_date_obj:
                    filtered_mrs.append(mr)
            except:
                continue
        
        # Filter issues
        filtered_issues = []
        for issue in user_issues:
            try:
                created_at = parse_gitlab_datetime(issue.get("created_at"))
                if created_at and start_date_obj <= created_at <= end_date_obj:
                    filtered_issues.append(issue)
            except:
                continue
        
        # Recalculate stats from filtered data
        commit_stats["total"] = len(filtered_commits)
        commit_stats["morning_commits"] = len([c for c in filtered_commits if (c.get("slot", "").lower()) == "morning"])
        commit_stats["afternoon_commits"] = len([c for c in filtered_commits if (c.get("slot", "").lower()) == "afternoon"])
        
        mr_stats["total"] = len(filtered_mrs)
        mr_stats["merged"] = len([m for m in filtered_mrs if (m.get("state", "").lower()) == "merged"])
        mr_stats["opened"] = len([m for m in filtered_mrs if (m.get("state", "").lower()) == "opened"])
        mr_stats["closed"] = len([m for m in filtered_mrs if (m.get("state", "").lower()) == "closed"])
        
        issue_stats["total"] = len(filtered_issues)
        issue_stats["opened"] = len([i for i in filtered_issues if (i.get("state", "").lower()) == "opened"])
        issue_stats["closed"] = len([i for i in filtered_issues if (i.get("state", "").lower()) == "closed"])
        
        # Update data references
        all_commits = filtered_commits
        user_mrs = filtered_mrs
        user_issues = filtered_issues
        
        st.info(f"📅 **Date Range Filter Active:** {st.session_state.filter_start_date} to {st.session_state.filter_end_date}")

    # --- Display ---

    # Projects
    st.markdown("---")
    st.subheader("📦 Projects")
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.metric("Personal Projects", len(personal_projects))
        if personal_projects:
            with st.expander("View Personal Projects"):
                for p in personal_projects:
                    st.write(f"- [{p['name_with_namespace']}]({p['web_url']})")
    with p_col2:
        st.metric("Contributed Projects", len(verified_contributed))
        if verified_contributed:
             with st.expander("View Contributed Projects"):
                for p in verified_contributed:
                    st.write(f"- [{p['name_with_namespace']}]({p['web_url']})")

    # Commits
    st.markdown("---")
    st.subheader("💻 Commits Analysis (IST)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Commits", commit_stats["total"])
    c2.metric("Morning (9:30-12:30)", commit_stats["morning_commits"])
    c3.metric("Afternoon (2:00-5:00)", commit_stats["afternoon_commits"])

    if all_commits:
        with st.expander("View Recent Commits"):
            # Use pandas for table
            df_commits = pd.DataFrame(all_commits)
            # Display updated columns
            st.dataframe(df_commits[["project_name", "message", "date", "time", "slot"]], width="stretch")
    else:
        if st.session_state.filter_applied:
            st.info(f"✅ No commits found in the selected date range ({st.session_state.filter_start_date} to {st.session_state.filter_end_date}).")
        else:
            st.info("No commits found.")

    # Groups
    st.markdown("---")
    st.subheader("👥 Groups")
    if user_groups:
        st.write(f"**Total Groups:** {len(user_groups)}")
        df_groups = pd.DataFrame(user_groups)
        st.dataframe(df_groups, width="stretch")
    else:
        st.info("No groups found.")

    # Merge Requests
    st.markdown("---")
    st.subheader("🔀 Merge Requests")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total MRs", mr_stats["total"])
    m2.metric("Merged", mr_stats["merged"])
    m3.metric("Open/Pending", mr_stats["opened"])
    m4.metric("Closed", mr_stats["closed"])

    if user_mrs:
        with st.expander("View MR Details"):
            df_mrs = pd.DataFrame(user_mrs)
            st.dataframe(df_mrs[["title", "role", "state", "created_at"]], width="stretch")
    else:
        if st.session_state.filter_applied:
            st.info(f"✅ No merge requests found in the selected date range ({st.session_state.filter_start_date} to {st.session_state.filter_end_date}).")
        else:
            st.info("No merge requests found.")

    # Issues
    st.markdown("---")
    st.subheader("⚠️ Issues")
    i1, i2, i3 = st.columns(3)
    i1.metric("Total Issues", issue_stats["total"])
    i2.metric("Open", issue_stats["opened"])
    i3.metric("Closed", issue_stats["closed"])

    if user_issues:
        with st.expander("View Issue Details"):
            df_issues = pd.DataFrame(user_issues)
            st.dataframe(df_issues[["title", "state", "created_at"]], width="stretch")
    else:
        if st.session_state.filter_applied:
            st.info(f"✅ No issues found in the selected date range ({st.session_state.filter_start_date} to {st.session_state.filter_end_date}).")
        else:
            st.info("No issues found.")
