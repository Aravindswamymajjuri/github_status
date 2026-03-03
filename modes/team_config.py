"""
Team Configuration Loader - Loads and parses team CSV configuration.

Supports loading team definitions from CSV with team names and member usernames.
Provides validation and team/member access patterns.
"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


class TeamConfig:
    """Manages team configuration from CSV files."""

    def __init__(self, csv_path: str = None):
        """
        Initialize TeamConfig with optional CSV path.

        Args:
            csv_path: Path to team CSV file (optional)
        """
        self.csv_path = csv_path
        self.teams_data: Optional[pd.DataFrame] = None
        self.teams_dict: Dict[str, List[str]] = {}  # {team_name: [members]}

        if csv_path:
            self.load_from_csv(csv_path)

    def load_from_csv(self, csv_path: str) -> bool:
        """
        Load team configuration from CSV file.

        Expected CSV format:
        team_name,username
        trioforce,aravindswamy
        trioforce,koushik_18
        trioforce,suma2304

        Args:
            csv_path: Path to CSV file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not Path(csv_path).exists():
                raise FileNotFoundError(f"CSV file not found: {csv_path}")

            self.teams_data = pd.read_csv(csv_path)

            # Validate required columns
            if not all(col in self.teams_data.columns for col in ["team_name", "username"]):
                raise ValueError("CSV must have 'team_name' and 'username' columns")

            # Build team dictionary
            self.teams_dict = {}
            for _, row in self.teams_data.iterrows():
                team_name = str(row["team_name"]).strip()
                username = str(row["username"]).strip()

                if team_name not in self.teams_dict:
                    self.teams_dict[team_name] = []

                if username not in self.teams_dict[team_name]:
                    self.teams_dict[team_name].append(username)

            return True
        except Exception as e:
            print(f"Error loading team config: {e}")
            return False

    def get_all_teams(self) -> List[str]:
        """
        Get list of all team names.

        Returns:
            List of team names
        """
        return sorted(self.teams_dict.keys())

    def get_team_members(self, team_name: str) -> List[str]:
        """
        Get list of members for a specific team.

        Args:
            team_name: Name of the team

        Returns:
            List of usernames in the team
        """
        return self.teams_dict.get(team_name, [])

    def get_all_members_as_flat_list(self) -> List[str]:
        """
        Get all members from all teams as a flat list (no duplicates).

        Returns:
            Deduplicated list of all usernames
        """
        all_members = set()
        for members in self.teams_dict.values():
            all_members.update(members)
        return sorted(all_members)

    def get_teams_for_member(self, username: str) -> List[str]:
        """
        Get all teams a member belongs to.

        Args:
            username: Username to search for

        Returns:
            List of team names member belongs to
        """
        teams = []
        for team_name, members in self.teams_dict.items():
            if username in members:
                teams.append(team_name)
        return teams

    def get_member_count(self, team_name: str) -> int:
        """
        Get number of members in a team.

        Args:
            team_name: Name of the team

        Returns:
            Number of members
        """
        return len(self.get_team_members(team_name))

    def is_valid_team(self, team_name: str) -> bool:
        """
        Check if team exists in configuration.

        Args:
            team_name: Name of team to check

        Returns:
            True if team exists
        """
        return team_name in self.teams_dict

    def is_valid_member(self, username: str) -> bool:
        """
        Check if member exists in any team.

        Args:
            username: Username to check

        Returns:
            True if user exists in any team
        """
        return username in self.get_all_members_as_flat_list()

    def get_as_dataframe(self) -> pd.DataFrame:
        """
        Get team configuration as DataFrame.

        Returns:
            DataFrame with team_name and username columns
        """
        if self.teams_data is not None:
            return self.teams_data.copy()
        return pd.DataFrame()

    def get_team_summary(self) -> pd.DataFrame:
        """
        Get summary statistics for teams.

        Returns:
            DataFrame with team_name and member_count columns
        """
        summary_data = []
        for team_name in self.get_all_teams():
            summary_data.append(
                {
                    "team_name": team_name,
                    "member_count": self.get_member_count(team_name),
                    "members": ", ".join(self.get_team_members(team_name)),
                }
            )
        return pd.DataFrame(summary_data)

    def add_team_member(self, team_name: str, username: str) -> bool:
        """
        Add a new member to a team.

        Args:
            team_name: Name of the team
            username: Username to add

        Returns:
            True if member was added successfully, False if already exists or error
        """
        try:
            team_name = str(team_name).strip()
            username = str(username).strip()

            if not team_name or not username:
                return False

            # If team doesn't exist, create it
            if team_name not in self.teams_dict:
                self.teams_dict[team_name] = []

            # Check if user already exists in this team
            if username in self.teams_dict[team_name]:
                return False  # User already in team

            # Add the user to the team
            self.teams_dict[team_name].append(username)

            # Update the dataframe
            self._rebuild_dataframe()
            return True
        except Exception as e:
            print(f"Error adding team member: {e}")
            return False

    def _rebuild_dataframe(self):
        """Rebuild the teams_data DataFrame from teams_dict."""
        rows = []
        for team_name, members in self.teams_dict.items():
            for username in members:
                rows.append({"team_name": team_name, "username": username})
        self.teams_data = pd.DataFrame(rows)

    def save_to_csv(self) -> bool:
        """
        Save the current team configuration to CSV file.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if not self.csv_path:
                raise ValueError("CSV path not set")

            # Rebuild dataframe to ensure it's in sync with teams_dict
            self._rebuild_dataframe()

            # Save to CSV
            self.teams_data.to_csv(self.csv_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving team config: {e}")
            return False

    def remove_team_member(self, team_name: str, username: str) -> bool:
        """
        Remove a member from a team.

        Args:
            team_name: Name of the team
            username: Username to remove

        Returns:
            True if member was removed, False otherwise
        """
        team_name = str(team_name).strip()
        username = str(username).strip()
        if not team_name or not username:
            return False
        if team_name not in self.teams_dict:
            return False
        if username not in self.teams_dict[team_name]:
            return False
        try:
            self.teams_dict[team_name].remove(username)
            self._rebuild_dataframe()
            if self.csv_path:
                self.teams_data.to_csv(self.csv_path, index=False)
            return True
        except Exception as e:
            print(f"Error removing member {username} from {team_name}: {e}")
            return False

    def remove_team(self, team_name: str) -> bool:
        """
        Delete an entire team from the configuration.

        Args:
            team_name: Name of the team to remove

        Returns:
            True if the team existed and was removed, False otherwise
        """
        team_name = str(team_name).strip()
        if not team_name or team_name not in self.teams_dict:
            return False
        try:
            # remove from dictionary
            del self.teams_dict[team_name]
            # rebuild data frame and save
            self._rebuild_dataframe()
            if self.csv_path:
                self.teams_data.to_csv(self.csv_path, index=False)
            return True
        except Exception as e:
            print(f"Error removing team {team_name}: {e}")
            return False


# Singleton instance for easy access
_team_config_instance: Optional[TeamConfig] = None


def get_team_config(csv_path: str = None) -> TeamConfig:
    """
    Get or create singleton TeamConfig instance.

    Args:
        csv_path: Path to CSV (only used for initialization)

    Returns:
        TeamConfig instance
    """
    global _team_config_instance

    if _team_config_instance is None:
        _team_config_instance = TeamConfig(csv_path)

    return _team_config_instance


def reload_team_config(csv_path: str) -> TeamConfig:
    """
    Force reload team configuration from CSV.

    Args:
        csv_path: Path to CSV file

    Returns:
        Reloaded TeamConfig instance
    """
    global _team_config_instance
    _team_config_instance = TeamConfig(csv_path)
    return _team_config_instance
