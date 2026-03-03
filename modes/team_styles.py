"""
CSS style constants for the Team Dashboard.

All HTML/CSS used in team_dashboard.py and team_views.py live here
so styling can be updated in one place.
"""

# ── Stat cards + badge pills ──────────────────────────────────────────────────
STAT_CARD_CSS: str = """
<style>
/* Light mode defaults */
.stat-card {
    background: linear-gradient(135deg, rgba(248,250,252,0.98), rgba(226,232,240,0.92));
    border: 1px solid rgba(148, 163, 184, 0.45);
    border-radius: 12px;
    padding: 1.2rem 1rem 1rem;
    text-align: center;
    margin-bottom: 1rem;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.15);
}
.stat-card h3 {
    margin: 0 0 0.3rem 0;
    font-size: 0.95rem;
    color: #334155;
    font-weight: 600;
}
.stat-card .value {
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0;
}
.stat-card .sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 0.3rem;
}
.stat-badges {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
    flex-wrap: wrap;
}
.stat-badge {
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-merged    { background: #d4edda; color: #155724; }
.badge-open      { background: #cce5ff; color: #004085; }
.badge-closed    { background: #f8d7da; color: #721c24; }
.badge-morning   { background: #fff3cd; color: #856404; }
.badge-afternoon { background: #d1ecf1; color: #0c5460; }
.badge-other     { background: #e2e3e5; color: #383d41; }

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    .stat-card {
        background: linear-gradient(135deg, rgba(30,41,59,0.78), rgba(15,23,42,0.72));
        border-color: rgba(148, 163, 184, 0.35);
        box-shadow: 0 6px 18px rgba(2, 6, 23, 0.35);
    }
    .stat-card h3  { color: #cbd5e1; }
    .stat-card .value { color: #f8fafc; text-shadow: 0 2px 10px rgba(15,23,42,0.6); }
    .stat-card .sub { color: #94a3b8; }
}
</style>
"""


# ── Reusable HTML builders ────────────────────────────────────────────────────


def commits_card(total: int, morning: int, afternoon: int, other: int = 0) -> str:
    """Return HTML for a Commits stat card."""
    return (
        f'<div class="stat-card">'
        f"<h3>Commits</h3>"
        f'<p class="value">{total}</p>'
        f'<div class="stat-badges">'
        f'<span class="stat-badge badge-morning">Morning {morning}</span>'
        f'<span class="stat-badge badge-afternoon">'
        f"Afternoon {afternoon}</span>"
        f'<span class="stat-badge badge-other">Other {other}</span>'
        f"</div></div>"
    )


def mr_card(total: int, merged: int, opened: int, closed: int) -> str:
    """Return HTML for a Merge Requests stat card."""
    return (
        f'<div class="stat-card">'
        f"<h3>Merge Requests</h3>"
        f'<p class="value">{total}</p>'
        f'<div class="stat-badges">'
        f'<span class="stat-badge badge-merged">Merged {merged}</span>'
        f'<span class="stat-badge badge-open">Open {opened}</span>'
        f'<span class="stat-badge badge-closed">Closed {closed}</span>'
        f"</div></div>"
    )


def issues_card(total: int, opened: int, closed: int) -> str:
    """Return HTML for an Issues stat card."""
    return (
        f'<div class="stat-card">'
        f"<h3>Issues</h3>"
        f'<p class="value">{total}</p>'
        f'<div class="stat-badges">'
        f'<span class="stat-badge badge-open">Open {opened}</span>'
        f'<span class="stat-badge badge-closed">Closed {closed}</span>'
        f"</div></div>"
    )


def simple_card(title: str, total: int) -> str:
    """Return HTML for a simple (count-only) stat card."""
    return f'<div class="stat-card"><h3>{title}</h3><p class="value">{total}</p></div>'
