import argparse
import streamlit as st
import pandas as pd
import io
import datetime
from gitlab_utils import batch
from gitlab_utils.date_range import (
    DateRangeValidationError,
    add_date_range_arguments,
    parse_date_range,
)

DEFAULT_ICFAI_USERS = """saikrishna_b
MohanaSriBhavitha
praneethashish
kanukuntagreeshma2004
vandana1735
vandana_rajuldev
Mukthanand21
Shanmukh16
Sathwikareddy_Damanagari
Sahasraa
laxmanreddypatlolla
Abhilash653
LagichettyKushal
Lakshy
Suma2304
koushik_18
kumari123
Habeebunissa
Bhaskar_Battula
Pranav_rs
Pavani_Pothuganti
prav2702"""

DEFAULT_RCTS_USERS = """vai5h
Saiharshavardhan
Rushika_1105
swarna_4539
satish05
aravindswamy
pavaninagireddi
jeevana_31
saiteja3005
SandhyaRani_111
klaxmi1908
Kaveri_Mamidi
dasari_Askhaya
Ashritha_P"""

IST_TIMEZONE = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def add_batch_date_range_arguments(parser):
    """
    Extend a parser with --from / --to range arguments.
    """
    return add_date_range_arguments(parser)


def build_batch_arg_parser():
    """
    Build a parser containing the batch date range arguments.
    """
    parser = argparse.ArgumentParser(add_help=False)
    return add_batch_date_range_arguments(parser)


def parse_batch_date_range(from_value=None, to_value=None, tz=IST_TIMEZONE):
    """
    Parse and validate date range values for batch handler/CLI usage.
    """
    return parse_date_range(from_value=from_value, to_value=to_value, tz=tz)


def _is_commit_in_range(commit_row, start_date, end_date):
    try:
        commit_date = datetime.datetime.strptime(commit_row.get("date", ""), "%Y-%m-%d").date()
        return start_date <= commit_date <= end_date
    except Exception:
        return False


def _is_created_at_in_range(item, start_dt, end_dt):
    created_at = item.get("created_at")
    if not created_at:
        return False
    try:
        created_dt = datetime.datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=datetime.timezone.utc)
        created_local = created_dt.astimezone(start_dt.tzinfo)
        return start_dt <= created_local <= end_dt
    except Exception:
        return False


def render_batch_mode_ui(client, report_type):
    st.subheader(f"🚀 Batch Analytics - {report_type}")

    default_value = DEFAULT_ICFAI_USERS if report_type == "ICFAI" else DEFAULT_RCTS_USERS
    results_key = f"batch_results_{report_type}"
    generated_at_key = f"batch_generated_at_{report_type}"
    active_range_key = f"batch_active_range_{report_type}"

    user_input = st.text_area(
        "Enter Usernames (one per line)",
        height=300,
        value=default_value,
        placeholder="user1\nuser2\n..."
    )

    if st.button("Run Batch Analysis", key=f"run_batch_{report_type}"):
        usernames = [line.strip() for line in user_input.splitlines() if line.strip()]
        if not usernames:
            st.warning("Please enter at least one username.")
            return

        st.info(f"Processing {len(usernames)} users...")

        with st.spinner("Fetching data in parallel..."):
            results = batch.process_batch_users(client, usernames)

        st.session_state[results_key] = results
        st.session_state[generated_at_key] = datetime.datetime.now(IST_TIMEZONE)
        st.session_state[active_range_key] = None

    if results_key not in st.session_state:
        return

    st.success("Batch processing complete!")

    st.write("#### Filter Existing Output by Date")
    range_col1, range_col2, range_col3 = st.columns([1, 1, 1])
    with range_col1:
        from_date_value = st.date_input(
            "From Date",
            value=None,
            format="YYYY-MM-DD",
            key=f"from_filter_{report_type}",
        )
    with range_col2:
        to_date_value = st.date_input(
            "To Date",
            value=None,
            format="YYYY-MM-DD",
            key=f"to_filter_{report_type}",
        )
    with range_col3:
        apply_filter_clicked = st.button("Apply Date Filter", key=f"apply_filter_{report_type}")

    if apply_filter_clicked:
        from_date_input = from_date_value.isoformat() if from_date_value else None
        to_date_input = to_date_value.isoformat() if to_date_value else None
        try:
            date_range = parse_batch_date_range(from_date_input, to_date_input)
        except DateRangeValidationError as exc:
            st.error(str(exc))
        else:
            st.session_state[active_range_key] = date_range

    active_range = st.session_state.get(active_range_key)
    if active_range:
        st.caption(
            f"Active filter: {active_range[0].strftime('%Y-%m-%d')} to {active_range[1].strftime('%Y-%m-%d')}"
        )
    else:
        st.caption("Active filter: None (showing all fetched results)")

    report_data = []
    for res in st.session_state[results_key]:
        u = res.get("username")
        status = res.get("status")
        err = res.get("error", "")
        data = res.get("data", {})
        projects = data.get("projects", {})

        c_stats = data.get("commit_stats", {"total": 0, "morning_commits": 0, "afternoon_commits": 0})
        m_stats = data.get("mr_stats", {"total": 0, "merged": 0, "opened": 0, "closed": 0})
        i_stats = data.get("issue_stats", {"total": 0, "opened": 0, "closed": 0})

        if active_range and status == "Success":
            start_dt, end_dt = active_range
            start_date, end_date = start_dt.date(), end_dt.date()
            commits_list = [c for c in data.get("commits", []) if _is_commit_in_range(c, start_date, end_date)]
            mrs_list = [m for m in data.get("mrs", []) if _is_created_at_in_range(m, start_dt, end_dt)]
            issues_list = [i for i in data.get("issues", []) if _is_created_at_in_range(i, start_dt, end_dt)]
            c_stats = {
                "total": len(commits_list),
                "morning_commits": sum(1 for c in commits_list if c.get("slot") == "Morning"),
                "afternoon_commits": sum(1 for c in commits_list if c.get("slot") == "Afternoon"),
            }
            opened_mrs = sum(1 for m in mrs_list if m.get("state") == "opened")
            m_stats = {
                "total": len(mrs_list),
                "merged": sum(1 for m in mrs_list if m.get("state") == "merged"),
                "closed": sum(1 for m in mrs_list if m.get("state") == "closed"),
                "opened": opened_mrs,
                "pending": opened_mrs,
            }
            i_stats = {
                "total": len(issues_list),
                "opened": sum(1 for i in issues_list if i.get("state") == "opened"),
                "closed": sum(1 for i in issues_list if i.get("state") == "closed"),
            }

        p_personal = len(projects.get("personal", []))
        p_contributed = len(projects.get("contributed", []))
        g_count = len(data.get("groups", []))

        row = {"Username": u, "Status": status}
        row["Report Date"] = st.session_state[generated_at_key].strftime("%Y-%m-%d")
        row["Report Time"] = st.session_state[generated_at_key].strftime("%I:%M %p")

        if status == "Success":
            if report_type == "ICFAI":
                row["Personal Projects"] = p_personal
                row["Contributed Projects"] = p_contributed
                row["Total Commits"] = c_stats["total"]
                row["Morning Count"] = c_stats["morning_commits"]
                row["Afternoon Count"] = c_stats["afternoon_commits"]
                row["MR Open"] = m_stats["opened"]
                row["MR Closed"] = m_stats["closed"]
                row["MR Merged"] = m_stats["merged"]
                row["Issues Open"] = i_stats["opened"]
                row["Issues Closed"] = i_stats["closed"]
                row["Groups Count"] = g_count
            elif report_type == "RCTS":
                row["Total Projects"] = p_personal + p_contributed
                row["Total Commits"] = c_stats["total"]
                row["MR Total"] = m_stats["total"]
                row["MR Merged"] = m_stats["merged"]
                row["MR Pending"] = m_stats["opened"]
                row["Issues Total"] = i_stats["total"]
                row["Groups"] = g_count
                row["Morning Active"] = "Yes" if c_stats["morning_commits"] > 0 else "No"
                row["Afternoon Active"] = "Yes" if c_stats["afternoon_commits"] > 0 else "No"
        else:
            row["Error"] = err

        report_data.append(row)

    # Display Summary
    st.write(f"### 📊 Batch Summary ({report_type})")
    df_report = pd.DataFrame(report_data)
    st.dataframe(df_report, width="stretch")

    # Export
    try:
        output = io.BytesIO()
        today = st.session_state[generated_at_key].strftime("%Y-%m-%d")
        filename = f"{report_type}_Report_{today}.xlsx"

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: Report
            df_report.to_excel(writer, index=False, sheet_name='Report')

            # Sheet 2: Raw Errors (if any)
            errors = [r for r in report_data if r.get("Status") == "Error"]
            if errors:
                pd.DataFrame(errors).to_excel(writer, index=False, sheet_name='Errors')

        st.download_button(
            label=f"Download {report_type} Report",
            data=output.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error creating Excel: {e}")
