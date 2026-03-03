from gitlab_utils.date_range import apply_range_params

def get_user_issues(client, user_id, date_range=None):
    """
    Fetch Issues:
    - Authored Issues (GET /issues?author_id=:id)

    Returns:
      - issues_list
      - stats: {total, opened, closed}
    """
    issues_list = []
    stats = {
        "total": 0,
        "opened": 0,
        "closed": 0
    }

    try:
        # GET /issues is available at instance level if authorized, or usually /issues?scope=all
        params = apply_range_params(
            {"author_id": user_id, "scope": "all"},
            date_range,
            "created_after",
            "created_before",
        )
        items = client._get_paginated("/issues", params=params, per_page=50, max_pages=10)

        for item in items:
            state = item.get("state")

            issues_list.append({
                "title": item.get("title"),
                "project_id": item.get("project_id"),
                "web_url": item.get("web_url"),
                "state": state,
                "created_at": item.get("created_at")
            })

            stats["total"] += 1
            if state == "opened":
                stats["opened"] += 1
            elif state == "closed":
                stats["closed"] += 1

    except Exception:
        pass

    return issues_list, stats
