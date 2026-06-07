"""
analytics.py
------------
Data analytics engine for GitHub repository data.
Processes raw API data into structured analytics and computes health scores.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional


class RepositoryAnalytics:
    """
    Transforms raw GitHub API data into rich analytics DataFrames
    and computes repository health metrics.
    """

    def __init__(self):
        self.commit_df: Optional[pd.DataFrame] = None
        self.contributor_df: Optional[pd.DataFrame] = None
        self.language_df: Optional[pd.DataFrame] = None
        self.repo_info: dict = {}

    # ------------------------------------------------------------------ #
    #  Data Loading                                                        #
    # ------------------------------------------------------------------ #

    def load_data(
        self,
        repo_info: dict,
        commits: list[dict],
        contributors: list[dict],
        languages: dict[str, int],
    ):
        """
        Load all raw data and prepare analytics DataFrames.

        Args:
            repo_info:    Repository metadata dict from GitHubAnalyzer.
            commits:      List of commit dicts.
            contributors: List of contributor dicts.
            languages:    Dict of {language: bytes}.
        """
        self.repo_info = repo_info
        self._prepare_commits(commits)
        self._prepare_contributors(contributors)
        self._prepare_languages(languages)

    def _prepare_commits(self, commits: list[dict]):
        """Build a datetime-indexed commit DataFrame."""
        if not commits:
            self.commit_df = pd.DataFrame(columns=['date', 'author', 'sha', 'message'])
            return

        df = pd.DataFrame(commits)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        df = df.sort_values('date')
        df['day'] = df['date'].dt.floor('D')
        df['week'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
        df['month'] = df['date'].dt.to_period('M').apply(lambda r: r.start_time)
        df['weekday'] = df['date'].dt.day_name()
        df['hour'] = df['date'].dt.hour
        self.commit_df = df

    def _prepare_contributors(self, contributors: list[dict]):
        """Build a ranked contributor DataFrame."""
        if not contributors:
            self.contributor_df = pd.DataFrame()
            return

        df = pd.DataFrame(contributors)
        df = df.sort_values('contributions', ascending=False).reset_index(drop=True)
        df.index += 1  # 1-based rank
        df.index.name = 'Rank'
        self.contributor_df = df

    def _prepare_languages(self, languages: dict[str, int]):
        """Build a language DataFrame with percentage shares."""
        if not languages:
            self.language_df = pd.DataFrame()
            return

        df = pd.DataFrame(
            list(languages.items()), columns=['Language', 'Bytes']
        ).sort_values('Bytes', ascending=False)
        total = df['Bytes'].sum()
        df['Percentage'] = (df['Bytes'] / total * 100).round(2)
        df['KB'] = (df['Bytes'] / 1024).round(1)
        self.language_df = df.reset_index(drop=True)

    # ------------------------------------------------------------------ #
    #  Commit Time-Series Aggregations                                     #
    # ------------------------------------------------------------------ #

    def daily_commits(self) -> pd.DataFrame:
        """Return daily commit counts for the analysis period."""
        if self.commit_df is None or self.commit_df.empty:
            return pd.DataFrame(columns=['day', 'commits'])
        return (
            self.commit_df.groupby('day')
            .size()
            .reset_index(name='commits')
            .rename(columns={'day': 'Date'})
        )

    def weekly_commits(self) -> pd.DataFrame:
        """Return weekly commit counts."""
        if self.commit_df is None or self.commit_df.empty:
            return pd.DataFrame(columns=['week', 'commits'])
        return (
            self.commit_df.groupby('week')
            .size()
            .reset_index(name='commits')
            .rename(columns={'week': 'Week'})
        )

    def monthly_commits(self) -> pd.DataFrame:
        """Return monthly commit counts."""
        if self.commit_df is None or self.commit_df.empty:
            return pd.DataFrame(columns=['month', 'commits'])
        return (
            self.commit_df.groupby('month')
            .size()
            .reset_index(name='commits')
            .rename(columns={'month': 'Month'})
        )

    def commit_trend(self) -> dict:
        """
        Compute a simple linear trend on weekly commits.

        Returns:
            dict with slope, direction, and percentage change.
        """
        weekly = self.weekly_commits()
        if len(weekly) < 4:
            return {'direction': 'insufficient data', 'slope': 0, 'pct_change': 0}

        x = np.arange(len(weekly))
        y = weekly['commits'].values
        slope, _ = np.polyfit(x, y, 1)

        first_half = y[: len(y) // 2].mean()
        second_half = y[len(y) // 2 :].mean()
        pct_change = ((second_half - first_half) / max(first_half, 1)) * 100

        return {
            'slope': round(slope, 3),
            'direction': 'increasing' if slope > 0.1 else ('decreasing' if slope < -0.1 else 'stable'),
            'pct_change': round(pct_change, 1),
            'avg_weekly': round(y.mean(), 1),
            'max_weekly': int(y.max()),
        }

    def busiest_days(self) -> pd.DataFrame:
        """Return commit counts grouped by weekday name."""
        if self.commit_df is None or self.commit_df.empty:
            return pd.DataFrame()
        order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        counts = self.commit_df['weekday'].value_counts().reindex(order, fill_value=0)
        return counts.reset_index().rename(columns={'index': 'Day', 'weekday': 'Commits'})

    # ------------------------------------------------------------------ #
    #  Health Score                                                        #
    # ------------------------------------------------------------------ #

    def compute_health_score(self) -> dict:
        """
        Compute a repository health score from 0–100.

        Scoring dimensions:
            Stars           (20 pts)  — popularity
            Forks           (15 pts)  — reusability
            Issue ratio     (15 pts)  — responsiveness
            Commit activity (25 pts)  — development velocity
            Contributors    (25 pts)  — community size

        Returns:
            dict with total score and per-dimension breakdown.
        """
        info = self.repo_info

        # — Stars score (logarithmic, saturates at 10 000)
        stars = info.get('stars', 0)
        stars_score = min(20, 20 * (np.log1p(stars) / np.log1p(10_000)))

        # — Forks score (logarithmic, saturates at 2 000)
        forks = info.get('forks', 0)
        forks_score = min(15, 15 * (np.log1p(forks) / np.log1p(2_000)))

        # — Issue responsiveness (lower open issues relative to forks = better)
        issues = info.get('open_issues', 0)
        if forks > 0:
            issue_ratio = issues / max(forks, 1)
            issue_score = max(0, 15 * (1 - min(issue_ratio / 10, 1)))
        else:
            issue_score = 10.0

        # — Commit activity in past 30 days
        recent_commits = 0
        if self.commit_df is not None and not self.commit_df.empty:
            cutoff = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
            recent_commits = int((self.commit_df['date'] >= cutoff).sum())
        commit_score = min(25, 25 * (np.log1p(recent_commits) / np.log1p(100)))

        # — Contributor diversity (saturates at 50)
        n_contributors = len(self.contributor_df) if self.contributor_df is not None else 0
        contrib_score = min(25, 25 * (np.log1p(n_contributors) / np.log1p(50)))

        total = stars_score + forks_score + issue_score + commit_score + contrib_score
        total = round(min(100, total), 1)

        return {
            'total': total,
            'grade': self._grade(total),
            'breakdown': {
                'Stars (Popularity)':       round(stars_score, 1),
                'Forks (Reusability)':      round(forks_score, 1),
                'Issue Responsiveness':     round(issue_score, 1),
                'Commit Activity':          round(commit_score, 1),
                'Contributor Community':    round(contrib_score, 1),
            },
            'max_scores': {
                'Stars (Popularity)': 20,
                'Forks (Reusability)': 15,
                'Issue Responsiveness': 15,
                'Commit Activity': 25,
                'Contributor Community': 25,
            },
        }

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 85:
            return 'A+'
        elif score >= 75:
            return 'A'
        elif score >= 65:
            return 'B'
        elif score >= 50:
            return 'C'
        elif score >= 35:
            return 'D'
        return 'F'

    # ------------------------------------------------------------------ #
    #  Summary Helper                                                      #
    # ------------------------------------------------------------------ #

    def summary_stats(self) -> dict:
        """Return a concise summary dict for display in the dashboard."""
        n_commits = len(self.commit_df) if self.commit_df is not None else 0
        n_contributors = len(self.contributor_df) if self.contributor_df is not None else 0
        top_language = (
            self.language_df.iloc[0]['Language']
            if self.language_df is not None and not self.language_df.empty
            else self.repo_info.get('main_language', 'Unknown')
        )

        return {
            'Total Commits (sampled)': n_commits,
            'Contributors': n_contributors,
            'Languages Used': len(self.language_df) if self.language_df is not None else 0,
            'Primary Language': top_language,
        }
