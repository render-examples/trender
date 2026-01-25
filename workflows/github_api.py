"""
GitHub API Client
Async GitHub API client with rate limiting and retry logic.
"""

import aiohttp
import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
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
                    
                    # Handle specific status codes using match-case
                    match response.status:
                        case 404:
                            return None
                        case 403:
                            error_msg = await response.text()
                            if 'rate limit' in error_msg.lower():
                                logger.error("GitHub rate limit exceeded")
                                return None
                            elif 'insufficient' in error_msg.lower():
                                logger.error("GitHub token has insufficient scopes")
                                return None
                            raise aiohttp.ClientError(f"GitHub API 403: {error_msg}")
                        case 422:
                            logger.error(f"GitHub API invalid query: {url}")
                            return None
                        case 503:
                            logger.warning("GitHub API temporarily unavailable (503)")
                            if attempt < retry_count - 1:
                                await asyncio.sleep(5)
                                continue
                            return None
                        case _:
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
                                 updated_since: datetime = None,
                                 created_since: datetime = None) -> List[Dict]:
        """
        Search repositories by language.

        Args:
            language: Programming language to filter by
            sort: Sort method (stars, forks, updated)
            updated_since: Only return repos updated since this date
            created_since: Only return repos created since this date

        Returns:
            List of repository data dictionaries
            Only includes repos with a valid (non-null, non-empty) language
        """
        query = f"language:{language}"
        if updated_since:
            query += f" pushed:>={updated_since.strftime('%Y-%m-%d')}"
        if created_since:
            query += f" created:>={created_since.strftime('%Y-%m-%d')}"

        url = f"{self.base_url}/search/repositories?q={query}&sort={sort}&per_page=50"
        result = await self._api_call(url)
        
        if not result:
            return []
        
        # Filter out repos without a language (defensive check, though API should return matching language)
        repos = [r for r in result.get('items', []) if r.get('language')]
        
        if len(repos) < len(result.get('items', [])):
            filtered_count = len(result.get('items', [])) - len(repos)
            logger.info(f"Filtered out {filtered_count} repos without language from search results")
        
        return repos

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
        Fetch README.md content (case insensitive), return first 5000 characters only.
        
        Args:
            owner: Repository owner
            repo: Repository name
        
        Returns:
            First 5000 characters of README, or None if not found
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
                    # Return first 5000 characters
                    return text[:5000]
            
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch README for {owner}/{repo}: {e}")
            return None

    async def search_repos_by_path(self, filename: str, limit: int = 50, created_since: datetime = None, 
                                   require_language: bool = True, default_language: str = None) -> List[Dict]:
        """
        Search for repositories containing a file in the root directory using code search.
        Uses GitHub's code search API which properly supports filename matching.
        
        Args:
            filename: Filename to search for (e.g., 'render.yaml')
            limit: Maximum number of results
            created_since: Only return repos created since this date (optional)
                          NOTE: Date filtering is done client-side after fetching repo details
                          because GitHub Code Search API doesn't support date filters.
            require_language: If True, filter out repos without language. If False, accept all repos.
            default_language: Default language to assign to repos without one (e.g., 'Unknown')
        
        Returns:
            List of repository data dictionaries ordered by stars descending
            All repos will have required fields: created_at, updated_at, description
        """
        # Use code search API which properly supports path/filename matching
        # NOTE: GitHub Code Search API does NOT support date filters (created:, pushed:, etc.)
        # We'll fetch more results and filter by date client-side
        query = f"filename:{filename}"
        
        # Request more results if date filtering is needed (since we'll filter client-side)
        per_page = 100 if created_since else 100
        
        url = f"{self.base_url}/search/code?q={query}&per_page={per_page}"
        
        logger.info(f"Searching for {filename} using code search API")
        
        result = await self._api_call(url)
        
        if not result or 'items' not in result:
            logger.warning(f"Code search returned no results for {filename}")
            return []
        
        # Extract unique repositories from code search results
        seen_repos = set()
        repos = []
        repos_without_language = 0
        repos_needing_details = []
        
        for item in result.get('items', []):
            repo_data = item.get('repository', {})
            repo_full_name = repo_data.get('full_name')
            repo_language = repo_data.get('language')
            
            # Handle repos without language
            if not repo_language:
                if require_language:
                    repos_without_language += 1
                    continue
                elif default_language:
                    # Assign default language
                    repo_data['language'] = default_language
            
            # Only include each repo once, and check if file is in root
            if repo_full_name and repo_full_name not in seen_repos:
                # Check if the file path is in root (no subdirectories)
                file_path = item.get('path', '')
                if file_path == filename:  # Exact match, no path prefix
                    seen_repos.add(repo_full_name)
                    
                    # Code search results don't include created_at, updated_at - need to fetch full details
                    if not repo_data.get('created_at') or not repo_data.get('updated_at'):
                        repos_needing_details.append(repo_full_name)
                    
                    repos.append(repo_data)
                    
                    if len(repos) >= limit:
                        break
        
        # Fetch full details for repos missing required fields
        if repos_needing_details:
            logger.info(f"Fetching full details for {len(repos_needing_details)} repos with missing fields")
            for repo_full_name in repos_needing_details:
                try:
                    owner, name = repo_full_name.split('/', 1)
                    full_details = await self.get_repo_details(owner, name)
                    
                    if full_details:
                        # Update the repo in our list with full details
                        for i, repo in enumerate(repos):
                            if repo.get('full_name') == repo_full_name:
                                # Preserve the language assignment (e.g., 'render')
                                preserved_language = repo.get('language')
                                repos[i] = full_details
                                if default_language and preserved_language == default_language:
                                    repos[i]['language'] = default_language
                                break
                except Exception as e:
                    logger.warning(f"Failed to fetch details for {repo_full_name}: {e}")
                    # Remove this repo from results since it lacks required fields
                    repos = [r for r in repos if r.get('full_name') != repo_full_name]
        
        # Final validation: ensure all repos have required fields and apply date filter
        validated_repos = []
        filtered_by_date = 0
        for repo in repos:
            if not (repo.get('created_at') and repo.get('updated_at')):
                logger.warning(f"Dropping repo {repo.get('full_name')} - missing required timestamps")
                continue
            
            # Apply client-side date filtering if created_since is specified
            if created_since:
                try:
                    # Parse ISO format datetime from GitHub API
                    created_at_str = repo.get('created_at', '')
                    # Handle both 'Z' and '+00:00' timezone formats
                    created_at_str = created_at_str.replace('Z', '+00:00')
                    created_at = datetime.fromisoformat(created_at_str)
                    
                    # Filter out repos created before the threshold
                    if created_at < created_since:
                        filtered_by_date += 1
                        continue
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse created_at for {repo.get('full_name')}: {e}")
                    # If we can't parse the date, skip this repo when date filtering is enabled
                    continue
            
            validated_repos.append(repo)
        
        # Sort by stars descending to prioritize quality
        validated_repos.sort(key=lambda r: r.get('stargazers_count', 0), reverse=True)
        
        # Log filtering statistics
        if repos_without_language > 0:
            logger.info(f"Filtered out {repos_without_language} repos without language")
        
        if filtered_by_date > 0:
            logger.info(f"Filtered out {filtered_by_date} repos created before {created_since.strftime('%Y-%m-%d')}")
        
        logger.info(f"Found {len(validated_repos)} unique repos with {filename} in root directory")
        
        return validated_repos[:limit]
    
    async def search_render_projects(self, limit: int = 50, created_since: datetime = None) -> List[Dict]:
        """
        Search for independent Render projects using code search.
        Finds repositories with render.yaml in root directory, sorted by stars.
        
        Special handling: Render projects often don't have a primary language detected by GitHub
        (e.g., documentation repos, config-only repos). We assign "render" (lowercase) as the
        language for ALL repos found via render.yaml search, regardless of GitHub's detection.
        This allows us to identify Render projects by language='render' instead of a separate flag.
        
        Args:
            limit: Maximum number of results to return
            created_since: Only return repos created since this date (optional)
        
        Returns:
            List of repository data dictionaries sorted by stars
            All repos will have language='render' (lowercase)
        """
        logger.info("=== Code search for render.yaml in root ===")
        if created_since:
            logger.info(f"Filtering for repos created since {created_since.strftime('%Y-%m-%d')}")
        
        try:
            # Code search for render.yaml in root
            # Don't require language, assign "render" (lowercase) as default for ALL repos
            repos = await self.search_repos_by_path(
                'render.yaml', 
                limit=limit, 
                created_since=created_since,
                require_language=False,  # Don't filter out repos without language
                default_language='render'  # Assign "render" (lowercase) as language
            )
            logger.info(f"Found {len(repos)} repos via code search (all assigned language='render')")
            return repos
        except Exception as e:
            logger.warning(f"Code search failed: {e}")
            return []
