"""
GitHub API Client
Async GitHub API client with rate limiting and retry logic.
"""

import aiohttp
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


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
        
        Returns:
            JSON response or None if error
        """
        # Check rate limit
        if self.rate_limit_remaining < 100:
            if self.rate_limit_reset:
                sleep_duration = max(self.rate_limit_reset - datetime.now(timezone.utc).timestamp(), 0)
                if sleep_duration > 0:
                    logger.warning(f"Rate limit low, sleeping {sleep_duration}s")
                    await asyncio.sleep(sleep_duration + 5)
        
        for attempt in range(retry_count):
            try:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    # Update rate limit info
                    self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
                    self.rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
                    
                    # Handle specific status codes
                    if response.status == 404:
                        return None
                    elif response.status == 403:
                        error_msg = await response.text()
                        if 'rate limit' in error_msg.lower():
                            logger.error("GitHub rate limit exceeded")
                            return None
                        elif 'insufficient' in error_msg.lower():
                            logger.error("GitHub token has insufficient scopes")
                            return None
                        raise aiohttp.ClientError(f"GitHub API 403: {error_msg}")
                    elif response.status == 422:
                        logger.error(f"GitHub API invalid query: {url}")
                        return None
                    elif response.status == 503:
                        logger.warning("GitHub API temporarily unavailable (503)")
                        if attempt < retry_count - 1:
                            await asyncio.sleep(5)
                            continue
                        return None
                    
                    response.raise_for_status()
                    
                    try:
                        return await response.json()
                    except json.JSONDecodeError:
                        logger.error("Failed to parse GitHub API JSON response")
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"GitHub API timeout (attempt {attempt + 1}/{retry_count})")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
            except aiohttp.ClientError as e:
                logger.warning(f"GitHub API error: {e} (attempt {attempt + 1}/{retry_count})")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return None
        
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

        url = f"{self.base_url}/search/repositories?q={query}&sort={sort}&per_page=50"
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
        Fetch README.md content (case insensitive), return first 80 words only.
        
        Args:
            owner: Repository owner
            repo: Repository name
        
        Returns:
            First 80 words of README, or None if not found
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/"
            result = await self._api_call(url)
            
            if not result or not isinstance(result, list):
                return None
            
            # Find readme.md (case insensitive)
            readme_file = None
            for file in result:
                if file.get('name', '').lower() == 'readme.md':
                    readme_file = file
                    break
            
            if not readme_file:
                return None
            
            # Fetch content
            content_url = readme_file.get('download_url')
            if not content_url:
                return None
            
            async with self.session.get(content_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    text = await response.text()
                    # Return first 80 words
                    words = text.split()[:80]
                    return ' '.join(words)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch README for {owner}/{repo}: {e}")
            return None

    async def search_by_topic(self, topic: str) -> List[Dict]:
        """
        Search repositories by topic.

        Args:
            topic: Topic to search for

        Returns:
            List of repository data dictionaries
        """
        url = f"{self.base_url}/search/repositories?q=topic:{topic}&per_page=50"
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
        url = f"{self.base_url}/search/code?q={keyword}+in:readme&per_page=50"
        result = await self._api_call(url)
        return result.get('items', []) if result else []

    async def search_repos_with_file(self, filename: str, limit: int = 50, 
                                      created_since: datetime = None) -> List[Dict]:
        """
        Search for repositories containing a specific file, ordered by creation date.
        For Render detection: searches repos with the file, then filters by creation date.
        
        Two-step approach:
        1. Code search for filename (GitHub Code Search doesn't support created: qualifier)
        2. Fetch full repo details to filter by creation date
        
        Args:
            filename: Filename to search for (e.g., 'render.yaml')
            limit: Maximum number of results
            created_since: Only include repos created after this date (default: 1 month ago)
        
        Returns:
            List of repository data dictionaries ordered by creation date descending
        """
        # Default to last month for fresh Render projects
        if not created_since:
            created_since = datetime.now(timezone.utc) - timedelta(days=30)
        
        logger.info(f"Step 1: Searching code for filename:{filename}")
        
        # Step 1: Code search (without date filter - not supported by GitHub Code Search API)
        url = f"{self.base_url}/search/code?q=filename:{filename}&per_page=100"
        result = await self._api_call(url)
        
        if not result or 'items' not in result:
            logger.warning(f"Code search returned no results for {filename}")
            return []
        
        logger.info(f"Code search found {len(result.get('items', []))} files")
        
        # Extract unique repository names from code search results
        seen_repos = set()
        repo_names = []
        
        for item in result['items']:
            repo_data = item.get('repository', {})
            repo_full_name = repo_data.get('full_name')
            
            if repo_full_name and repo_full_name not in seen_repos:
                seen_repos.add(repo_full_name)
                repo_names.append(repo_full_name)
        
        logger.info(f"Step 2: Fetching full details for {len(repo_names)} unique repos")
        
        # Step 2: Fetch full repo details to get accurate creation dates
        repos_with_details = []
        
        for repo_full_name in repo_names:
            if '/' not in repo_full_name:
                continue
                
            owner, repo = repo_full_name.split('/', 1)
            repo_details = await self.get_repo_details(owner, repo)
            
            if repo_details:
                repos_with_details.append(repo_details)
        
        logger.info(f"Successfully fetched {len(repos_with_details)} repo details")
        
        # Filter by creation date
        filtered_repos = []
        for repo in repos_with_details:
            created_at_str = repo.get('created_at')
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if created_at >= created_since:
                        filtered_repos.append(repo)
                except (ValueError, AttributeError):
                    continue
        
        logger.info(f"Filtered to {len(filtered_repos)} repos created since {created_since.strftime('%Y-%m-%d')}")
        
        # Sort by creation date descending (newest first)
        filtered_repos.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        
        # Return top N
        result = filtered_repos[:limit]
        logger.info(f"Returning top {len(result)} repos")
        return result

    async def get_org_repos(self, org: str) -> List[Dict]:
        """
        Get all repositories for an organization.

        Args:
            org: Organization name

        Returns:
            List of repository data dictionaries
        """
        url = f"{self.base_url}/orgs/{org}/repos?per_page=50"
        result = await self._api_call(url)
        return result if isinstance(result, list) else []
