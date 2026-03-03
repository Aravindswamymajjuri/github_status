from modes import team_styles


def test_team_style_card_builders_include_counts():
    commits_html = team_styles.commits_card(10, 4, 6)
    mr_html = team_styles.mr_card(8, 2, 3, 3)
    issues_html = team_styles.issues_card(5, 3, 2)
    simple_html = team_styles.simple_card("Projects", 7)

    assert "Commits" in commits_html and "Morning 4" in commits_html and "Afternoon 6" in commits_html
    assert "Merge Requests" in mr_html and "Merged 2" in mr_html and "Closed 3" in mr_html
    assert "Issues" in issues_html and "Open 3" in issues_html and "Closed 2" in issues_html
    assert "Projects" in simple_html and ">7<" in simple_html
