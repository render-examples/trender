"""
GitHub API Client
Async GitHub API client with rate limiting and retry logic.
"""

import aiohttp
import asyncio
import base64
from datetime import datetime
from typing import Dict, List, Optional


class GitHubAPIClient:
    """Async GitHub API client with token authentication.
    
    Supports both OAuth App tokens and Personal Access Tokens (PAT).
    """

    def __init__(self, access_token: str):
        """
        Initialize GitHub API client with a GitHub access token.
        
        Args:
            access_token: GitHub access token - can be either:
                         - Personal Access Token (PAT) from GitHub settings
                         - OAuth token from OAuth App flow
                         Both work identically for API access.
        """
        self.access_token = access_token
        self.base_url = "https://api.github.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            'Authorization': f'token {self.access_token}',
            'Accept': 'application/vnd.github.v3+json'
        })
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()

    async def _api_call(self, url: str, retry_count: int = 3) -> dict:
        """
        Make API call with rate limiting and retry logic.

        Args:
            url: The API endpoint URL
            retry_count: Number of retries on failure

        Returns:
            JSON response from the API
        """
        # Check rate limit
        if self.rate_limit_remaining < 100:
            if self.rate_limit_reset:
                sleep_duration = max(self.rate_limit_reset - datetime.utcnow().timestamp(), 0)
                await asyncio.sleep(sleep_duration + 5)

        for attempt in range(retry_count):
            try:
                async with self.session.get(url) as response:
                    # Update rate limit info
                    self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
                    self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))

                    if response.status == 404:
                        return None

                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                if attempt == retry_count - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return None

    async def search_repositories(self, language: str, sort: str = 'stars',
                                 updated_since: datetime = None) -> List[Dict]:
        """
        Search repositories by language.

        Args:
            language: Programming language to filter by
            sort: Sort method (stars, forks, updated)
            updated_since: Only return repos updated since this date

        Returns:
            List of repository data dictionaries
        """
        query = f"language:{language}"
        if updated_since:
            query += f" pushed:>={updated_since.strftime('%Y-%m-%d')}"

        url = f"{self.base_url}/search/repositories?q={query}&sort={sort}&per_page=100"
        result = await self._api_call(url)
        return result.get('items', []) if result else []

    async def get_repo_details(self, owner: str, repo: str) -> Dict:
        """
        Get detailed repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository data dictionary
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        return await self._api_call(url)

    async def get_commits(self, owner: str, repo: str, since: datetime) -> List[Dict]:
        """
        Get commits since a specific date.

        Args:
            owner: Repository owner
            repo: Repository name
            since: Get commits since this datetime

        Returns:
            List of commit data dictionaries
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits?since={since.isoformat()}"
        result = await self._api_call(url)
        return result if isinstance(result, list) else []

    async def get_issues(self, owner: str, repo: str, state: str = 'closed',
                        since: datetime = None) -> List[Dict]:
        """
        Get issues for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            since: Get issues since this datetime

        Returns:
            List of issue data dictionaries
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues?state={state}"
        if since:
            url += f"&since={since.isoformat()}"
        result = await self._api_call(url)
        return result if isinstance(result, list) else []

    async def get_contributors(self, owner: str, repo: str) -> List[Dict]:
        """
        Get repository contributors.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of contributor data dictionaries
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
        result = await self._api_call(url)
        return result if isinstance(result, list) else []

    async def get_file_contents(self, owner: str, repo: str, path: str) -> Optional[str]:
        """
        Get file contents from repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to file in repository

        Returns:
            File contents as string, or None if not found
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            result = await self._api_call(url)
            if result and 'content' in result:
                return base64.b64decode(result['content']).decode('utf-8')
            return None
        except Exception:
            return None

    async def fetch_readme(self, owner: str, repo: str) -> Optional[str]:
        """
        Fetch README content from repository.
        Tries common README filenames (README.md, README.rst, README.txt, README).

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            README content as string, or None if not found
        """
        readme_filenames = ['README.md', 'readme.md', 'README.rst', 'README.txt', 'README']
        
        for filename in readme_filenames:
            content = await self.get_file_contents(owner, repo, filename)
            if content:
                return content
        
        return None

    async def search_by_topic(self, topic: str) -> List[Dict]:
        """
        Search repositories by topic.

        Args:
            topic: Topic to search for

        Returns:
            List of repository data dictionaries
        """
        url = f"{self.base_url}/search/repositories?q=topic:{topic}&per_page=100"
        result = await self._api_call(url)
        return result.get('items', []) if result else []

    async def search_readme_mentions(self, keyword: str) -> List[Dict]:
        """
        Search for keyword mentions in README files.

        Args:
            keyword: Keyword to search for

        Returns:
            List of search result dictionaries
        """
        url = f"{self.base_url}/search/code?q={keyword}+in:readme&per_page=100"
        result = await self._api_call(url)
        return result.get('items', []) if result else []

    async def get_org_repos(self, org: str) -> List[Dict]:
        """
        Get all repositories for an organization.

        Args:
            org: Organization name

        Returns:
            List of repository data dictionaries
        """
        url = f"{self.base_url}/orgs/{org}/repos?per_page=100"
        result = await self._api_call(url)
        return result if isinstance(result, list) else []
