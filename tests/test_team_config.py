from pathlib import Path

from modes import team_config


def _write_csv(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def test_team_config_loads_csv_and_exposes_members(tmp_path):
    csv_file = tmp_path / "teams.csv"
    _write_csv(
        csv_file,
        "team_name,username\nalpha,alice\nalpha,bob\nbeta,bob\n",
    )

    cfg = team_config.TeamConfig(str(csv_file))

    assert cfg.get_all_teams() == ["alpha", "beta"]
    assert cfg.get_team_members("alpha") == ["alice", "bob"]
    assert cfg.get_all_members_as_flat_list() == ["alice", "bob"]
    assert cfg.get_teams_for_member("bob") == ["alpha", "beta"]
    assert cfg.get_member_count("alpha") == 2
    assert cfg.is_valid_team("alpha")
    assert cfg.is_valid_member("alice")


def test_team_config_rejects_invalid_csv_schema(tmp_path):
    csv_file = tmp_path / "bad.csv"
    _write_csv(csv_file, "name,user\nalpha,alice\n")

    cfg = team_config.TeamConfig()
    assert cfg.load_from_csv(str(csv_file)) is False


def test_add_team_member_and_remove_team(tmp_path):
    csv_file = tmp_path / "teams.csv"
    _write_csv(csv_file, "team_name,username\nalpha,alice\n")
    cfg = team_config.TeamConfig(str(csv_file))

    assert cfg.add_team_member("alpha", "bob") is True
    assert cfg.add_team_member("alpha", "bob") is False
    assert cfg.add_team_member(" ", "bob") is False
    assert cfg.get_team_members("alpha") == ["alice", "bob"]

    assert cfg.remove_team("alpha") is True
    assert cfg.remove_team("alpha") is False
    assert cfg.get_all_teams() == []


def test_save_to_csv_persists_current_state(tmp_path):
    csv_file = tmp_path / "teams.csv"
    _write_csv(csv_file, "team_name,username\nalpha,alice\n")
    cfg = team_config.TeamConfig(str(csv_file))
    cfg.add_team_member("alpha", "bob")

    assert cfg.save_to_csv() is True
    content = csv_file.read_text(encoding="utf-8")
    assert "team_name,username" in content
    assert "alpha,alice" in content
    assert "alpha,bob" in content


def test_get_team_summary_and_dataframe_methods(tmp_path):
    csv_file = tmp_path / "teams.csv"
    _write_csv(csv_file, "team_name,username\nalpha,alice\nalpha,bob\n")
    cfg = team_config.TeamConfig(str(csv_file))

    df = cfg.get_as_dataframe()
    summary = cfg.get_team_summary()

    assert len(df) == 2
    assert len(summary) == 1


def test_singleton_get_and_reload_team_config(tmp_path):
    csv_file_1 = tmp_path / "teams1.csv"
    csv_file_2 = tmp_path / "teams2.csv"
    _write_csv(csv_file_1, "team_name,username\nalpha,alice\n")
    _write_csv(csv_file_2, "team_name,username\nbeta,bob\n")

    team_config._team_config_instance = None
    cfg1 = team_config.get_team_config(str(csv_file_1))
    cfg2 = team_config.get_team_config(str(csv_file_2))
    reloaded = team_config.reload_team_config(str(csv_file_2))

    assert cfg1 is cfg2
    assert reloaded.get_all_teams() == ["beta"]
