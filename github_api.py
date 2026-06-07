"""
github_api.py
-------------
GitHub API interaction layer using PyGithub.
Handles all data fetching, validation, and rate limit management.
"""

import re
import time
import requests
from datetime import datetime, timezone
from typing import Optional
from github import Github, GithubException, RateLimitExceededException


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    pass


class RateLimitError(GitHubAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class RepoNotFoundError(GitHubAPIError):
    """Raised when repository is not found."""
    pass


class ConnectionError(GitHubAPIError):
    """Raised when internet connection fails."""
    pass


class GitHubAnalyzer:
    """
    Core GitHub API wrapper providing data fetching capabilities
    for repository analysis.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub client.

        Args:
            token: Optional GitHub personal access token for higher rate limits.
                   Without token: 60 requests/hr. With token: 5000 requests/hr.
        """
        try:
            self.github = Github(token) if token else Github()
            self.repo = None
            self._cached_data = {}
        except Exception as e:
            raise ConnectionError(f"Failed to initialize GitHub client: {e}")

    def validate_url(self, url: str) -> tuple[str, str]:
        """
        Parse and validate a GitHub repository URL.

        Args:
            url: GitHub repository URL (e.g. https://github.com/owner/repo)

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            ValueError: If URL format is invalid.
        """
        url = url.strip().rstrip('/')

        # Support shorthand "owner/repo" format
        if re.match(r'^[\w.-]+/[\w.-]+$', url):
            parts = url.split('/')
            return parts[0], parts[1]

        # Full GitHub URL patterns
        patterns = [
            r'https?://github\.com/([\w.-]+)/([\w.-]+)',
            r'github\.com/([\w.-]+)/([\w.-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(
            "Invalid GitHub URL. Expected format: https://github.com/owner/repo"
        )

    def load_repository(self, url: str) -> dict:
        """
        Load a GitHub repository and return its basic metadata.

        Args:
            url: GitHub repository URL

        Returns:
            dict with repository metadata

        Raises:
            RepoNotFoundError, RateLimitError, ConnectionError
        """
        try:
            owner, repo_name = self.validate_url(url)
            self.repo = self.github.get_repo(f"{owner}/{repo_name}")
            self._cached_data = {}  # Clear cache for new repo

            return {
                'name': self.repo.name,
                'full_name': self.repo.full_name,
                'owner': self.repo.owner.login,
                'description': self.repo.description or 'No description provided.',
                'stars': self.repo.stargazers_count,
                'forks': self.repo.forks_count,
                'open_issues': self.repo.open_issues_count,
                'watchers': self.repo.watchers_count,
                'main_language': self.repo.language or 'Unknown',
                'created_at': self.repo.created_at,
                'updated_at': self.repo.updated_at,
                'url': self.repo.html_url,
                'topics': self.repo.get_topics(),
                'license': self.repo.license.name if self.repo.license else 'None',
                'default_branch': self.repo.default_branch,
                'size_kb': self.repo.size,
                'archived': self.repo.archived,
                'is_fork': self.repo.fork,
            }

        except RateLimitExceededException:
            reset_time = self.github.get_rate_limit().core.reset
            wait = int((reset_time - datetime.now(timezone.utc)).total_seconds())
            raise RateLimitError(
                f"GitHub API rate limit exceeded. Resets in {max(wait, 0)} seconds."
            )
        except GithubException as e:
            if e.status == 404:
                raise RepoNotFoundError(
                    f"Repository not found. Check the URL and ensure it is public."
                )
            raise GitHubAPIError(f"GitHub API error {e.status}: {e.data.get('message', str(e))}")
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "No internet connection. Please check your network and try again."
            )

    def get_contributors(self, max_contributors: int = 30) -> list[dict]:
        """
        Fetch top contributors and their commit counts.

        Args:
            max_contributors: Maximum number of contributors to return.

        Returns:
            List of contributor dicts sorted by commit count.
        """
        if 'contributors' in self._cached_data:
            return self._cached_data['contributors']

        if not self.repo:
            raise GitHubAPIError("No repository loaded.")

        try:
            contributors = []
            for contributor in self.repo.get_contributors():
                if len(contributors) >= max_contributors:
                    break
                contributors.append({
                    'login': contributor.login,
                    'avatar_url': contributor.avatar_url,
                    'contributions': contributor.contributions,
                    'profile_url': contributor.html_url,
                    'name': contributor.name or contributor.login,
                })

            # Calculate contribution percentages
            total = sum(c['contributions'] for c in contributors)
            for c in contributors:
                c['percentage'] = round((c['contributions'] / total * 100), 2) if total > 0 else 0

            self._cached_data['contributors'] = contributors
            return contributors

        except RateLimitExceededException:
            raise RateLimitError("Rate limit exceeded while fetching contributors.")
        except GithubException as e:
            raise GitHubAPIError(f"Error fetching contributors: {e}")

    def get_commit_activity(self, days: int = 365) -> list[dict]:
        """
        Fetch commit history for the past N days.

        Args:
            days: Number of days of history to fetch.

        Returns:
            List of commit dicts with date, author, and message.
        """
        if 'commits' in self._cached_data:
            return self._cached_data['commits']

        if not self.repo:
            raise GitHubAPIError("No repository loaded.")

        try:
            from datetime import timedelta
            since = datetime.now(timezone.utc) - timedelta(days=days)
            commits = []

            for commit in self.repo.get_commits(since=since):
                commit_date = commit.commit.author.date
                # Normalize to UTC-aware datetime
                if commit_date.tzinfo is None:
                    commit_date = commit_date.replace(tzinfo=timezone.utc)

                commits.append({
                    'sha': commit.sha[:7],
                    'date': commit_date,
                    'author': commit.commit.author.name,
                    'message': commit.commit.message.split('\n')[0][:80],
                })

                # Safety limit to avoid exhausting rate limit
                if len(commits) >= 1000:
                    break

            self._cached_data['commits'] = commits
            return commits

        except RateLimitExceededException:
            raise RateLimitError("Rate limit exceeded while fetching commits.")
        except GithubException as e:
            raise GitHubAPIError(f"Error fetching commits: {e}")

    def get_languages(self) -> dict[str, int]:
        """
        Fetch language breakdown (bytes of code per language).

        Returns:
            Dict mapping language name → bytes of code.
        """
        if 'languages' in self._cached_data:
            return self._cached_data['languages']

        if not self.repo:
            raise GitHubAPIError("No repository loaded.")

        try:
            languages = dict(self.repo.get_languages())
            self._cached_data['languages'] = languages
            return languages
        except GithubException as e:
            raise GitHubAPIError(f"Error fetching languages: {e}")

    def get_total_commits(self) -> int:
        """
        Estimate total commit count using contributor contributions.

        Returns:
            Approximate total commit count.
        """
        if 'total_commits' in self._cached_data:
            return self._cached_data['total_commits']

        try:
            contributors = self.get_contributors(max_contributors=100)
            total = sum(c['contributions'] for c in contributors)
            self._cached_data['total_commits'] = total
            return total
        except Exception:
            return 0

    def check_rate_limit(self) -> dict:
        """
        Check current API rate limit status.

        Returns:
            Dict with remaining requests and reset time.
        """
        try:
            rate = self.github.get_rate_limit().core
            return {
                'remaining': rate.remaining,
                'limit': rate.limit,
                'reset_at': rate.reset,
            }
        except Exception:
            return {'remaining': 'Unknown', 'limit': 60, 'reset_at': None}
