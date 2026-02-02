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

RENDER_REPOS_PER_PAGE = 100  # Number of results to fetch when searching for render.yaml


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

    async def _handle_response_status(self, response: aiohttp.ClientResponse, url: str, 
                                      attempt: int, retry_count: int) -> tuple[bool, Optional[dict]]:
        """
        Handle HTTP response status codes and errors.
        
        Args:
            response: The aiohttp response object
            url: The URL that was called
            attempt: Current retry attempt number
            retry_count: Total number of retries allowed
        
        Returns:
            Tuple of (should_retry, result)
            - should_retry: True if the request should be retried
            - result: The parsed JSON result if successful, None otherwise
        """
        match response.status:
            case 404:
                return (False, None)
            
            case 403:
                error_msg = await response.text()
                if 'rate limit' in error_msg.lower():
                    logger.error("GitHub rate limit exceeded")
                    return (False, None)
                elif 'insufficient' in error_msg.lower():
                    logger.error("GitHub token has insufficient scopes")
                    return (False, None)
                raise aiohttp.ClientError(f"GitHub API 403: {error_msg}")
            
            case 422:
                logger.error(f"GitHub API invalid query: {url}")
                return (False, None)
            
            case 503:
                logger.warning("GitHub API temporarily unavailable (503)")
                if attempt < retry_count - 1:
                    await asyncio.sleep(5)
                    return (True, None)  # Retry
                return (False, None)
            
            case _:
                response.raise_for_status()
        
        # If we get here, response was successful
        try:
            result = await response.json()
            return (False, result)
        except json.JSONDecodeError:
            logger.error("Failed to parse GitHub API JSON response")
            return (False, None)

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
                    
                    # Handle response status and errors
                    should_retry, result = await self._handle_response_status(response, url, attempt, retry_count)
                    
                    if should_retry:
                        continue  # Retry the request
                    
                    return result
                        
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

    def _should_include_repo(self, repo_language: Optional[str], require_language: bool) -> bool:
        """Check if a repo should be included based on language requirements."""
        if repo_language:
            return True
        return not require_language
    
    def _is_file_in_root(self, file_path: str, filename: str) -> bool:
        """Check if file is in root directory (no subdirectories)."""
        return file_path == filename
    
    def _parse_created_date(self, repo: Dict) -> Optional[datetime]:
        """Parse created_at date from repo data."""
        try:
            created_at_str = repo.get('created_at', '')
            # Handle both 'Z' and '+00:00' timezone formats
            created_at_str = created_at_str.replace('Z', '+00:00')
            return datetime.fromisoformat(created_at_str)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse created_at for {repo.get('full_name')}: {e}")
            return None
    
    def _is_repo_valid(self, repo: Dict, created_since: Optional[datetime]) -> bool:
        """Validate repo has required fields and meets date filter."""
        # Check required fields
        if not (repo.get('created_at') and repo.get('updated_at')):
            logger.warning(f"Dropping repo {repo.get('full_name')} - missing required timestamps")
            return False
        
        # Check date filter if specified
        if created_since:
            created_at = self._parse_created_date(repo)
            if not created_at or created_at < created_since:
                return False
        
        return True
    
    async def _fetch_missing_repo_details(self, repos: List[Dict], repos_needing_details: List[str], 
                                         default_language: Optional[str]) -> List[Dict]:
        """Fetch full details for repos missing required fields using batched async calls."""
        if not repos_needing_details:
            return repos
        
        logger.info(f"Fetching full details for {len(repos_needing_details)} repos with missing fields (batched)")
        
        # Create a mapping for quick lookup
        repos_by_name = {repo.get('full_name'): repo for repo in repos}
        
        # Prepare all API calls to run in parallel
        async def fetch_one_repo(repo_full_name: str) -> tuple[str, Optional[Dict]]:
            """Fetch a single repo's details, returning (repo_name, details)."""
            try:
                owner, name = repo_full_name.split('/', 1)
                full_details = await self.get_repo_details(owner, name)
                return (repo_full_name, full_details)
            except Exception as e:
                logger.warning(f"Failed to fetch details for {repo_full_name}: {e}")
                return (repo_full_name, None)
        
        # Batch all API calls concurrently using asyncio.gather
        fetch_tasks = [fetch_one_repo(repo_name) for repo_name in repos_needing_details]
        results = await asyncio.gather(*fetch_tasks, return_exceptions=False)
        
        # Process results
        for repo_full_name, full_details in results:
            if full_details:
                # Preserve default language assignment if it was set
                original_repo = repos_by_name.get(repo_full_name, {})
                preserved_language = original_repo.get('language')
                
                if default_language and preserved_language == default_language:
                    full_details['language'] = default_language
                
                repos_by_name[repo_full_name] = full_details
            else:
                # Remove repos that failed to fetch
                repos_by_name.pop(repo_full_name, None)
        
        return list(repos_by_name.values())
    
    def _extract_unique_repos(self, items: List[Dict], filename: str, limit: int,
                             require_language: bool, default_language: Optional[str]) -> tuple[List[Dict], List[str], int]:
        """Extract unique repositories from code search results."""
        seen_repos = set()
        repos = []
        repos_needing_details = []
        repos_without_language = 0
        
        for item in items:
            repo_data = item.get('repository', {})
            repo_full_name = repo_data.get('full_name')
            repo_language = repo_data.get('language')
            
            # Skip if already seen
            if not repo_full_name or repo_full_name in seen_repos:
                continue
            
            # Skip if not in root directory
            if not self._is_file_in_root(item.get('path', ''), filename):
                continue
            
            # Handle language requirements
            if not repo_language:
                if require_language:
                    repos_without_language += 1
                    continue
                elif default_language:
                    repo_data['language'] = default_language
            
            # Add to results
            seen_repos.add(repo_full_name)
            repos.append(repo_data)
            
            # Track repos needing full details
            if not repo_data.get('created_at') or not repo_data.get('updated_at'):
                repos_needing_details.append(repo_full_name)
            
            if len(repos) >= limit:
                break
        
        return repos, repos_needing_details, repos_without_language
    
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
        # Build and execute search query
        query = f"filename:{filename}"
        url = f"{self.base_url}/search/code?q={query}&per_page={RENDER_REPOS_PER_PAGE}"
        
        logger.info(f"Searching for {filename} using code search API")
        result = await self._api_call(url)
        
        if not result or 'items' not in result:
            logger.warning(f"Code search returned no results for {filename}")
            return []
        
        # Extract unique repositories from search results
        repos, repos_needing_details, repos_without_language = self._extract_unique_repos(
            result.get('items', []), filename, limit, require_language, default_language
        )
        
        # Fetch full details for repos missing required fields
        repos = await self._fetch_missing_repo_details(repos, repos_needing_details, default_language)
        
        # Validate and filter repos
        validated_repos = [repo for repo in repos if self._is_repo_valid(repo, created_since)]
        
        # Sort by stars descending
        validated_repos.sort(key=lambda r: r.get('stargazers_count', 0), reverse=True)
        
        # Log statistics
        if repos_without_language > 0:
            logger.info(f"Filtered out {repos_without_language} repos without language")
        
        filtered_by_date = len(repos) - len(validated_repos)
        if filtered_by_date > 0 and created_since:
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
        
        Hardcoded repos: To ensure we always have high-quality examples, we hardcode several
        prominent Render repositories that may not have render.yaml in their root.
        
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
        
        # Hardcoded prominent Render repositories
        hardcoded_repos = [
            'Flagsmith/flagsmith',
            'run-llama/sec-insights',
            'postalsys/emailengine',
            'spree/spree_starter',
            'ryanwi/rails7-on-docker',
            'frolic/ethfs',
        ]
        
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
            
            # Fetch hardcoded repos in parallel
            logger.info(f"Fetching {len(hardcoded_repos)} hardcoded Render showcase repos")
            hardcoded_fetch_tasks = []
            for repo_full_name in hardcoded_repos:
                try:
                    owner, name = repo_full_name.split('/', 1)
                    hardcoded_fetch_tasks.append(self.get_repo_details(owner, name))
                except ValueError:
                    logger.warning(f"Invalid hardcoded repo format: {repo_full_name}")
                    continue
            
            # Fetch all hardcoded repos concurrently
            hardcoded_results = await asyncio.gather(*hardcoded_fetch_tasks, return_exceptions=True)
            
            # Process hardcoded repos
            hardcoded_valid = []
            for i, result in enumerate(hardcoded_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch hardcoded repo {hardcoded_repos[i]}: {result}")
                    continue
                if result and isinstance(result, dict):
                    # Assign 'render' language and validate (without date filter for hardcoded repos)
                    result['language'] = 'render'
                    # Validate required fields but skip date filter for hardcoded showcase repos
                    if self._is_repo_valid(result, created_since=None):
                        hardcoded_valid.append(result)
                        logger.info(f"Added hardcoded repo: {result.get('full_name')} ({result.get('stargazers_count', 0)} stars)")
                    else:
                        logger.warning(f"Hardcoded repo {hardcoded_repos[i]} failed validation: {result.get('full_name')}")
            
            # Merge hardcoded repos with search results, avoiding duplicates
            seen_repos = {repo.get('full_name') for repo in repos if repo.get('full_name')}
            for hardcoded_repo in hardcoded_valid:
                if hardcoded_repo.get('full_name') not in seen_repos:
                    repos.append(hardcoded_repo)
                    seen_repos.add(hardcoded_repo.get('full_name'))
            
            # Sort all repos by stars descending
            repos.sort(key=lambda r: r.get('stargazers_count', 0), reverse=True)
            
            logger.info(f"Total repos after merging: {len(repos)} (including {len(hardcoded_valid)} hardcoded)")
            
            return repos[:limit]
        except Exception as e:
            logger.warning(f"Code search failed: {e}")
            return []
