"""
Shared Resource Management
Handles initialization and cleanup of shared resources like GitHub API client and database pool.
"""

import asyncpg
import asyncio
import os
from github_api import GitHubAPIClient


async def init_connections():
    """
    Initialize shared GitHub API client and database connection pool with error handling.
    
    Returns:
        Tuple of (GitHubAPIClient, asyncpg.Pool)
        
    Raises:
        ValueError: If required environment variables are missing
        ConnectionError: If connections cannot be established
    """
    # #region agent log
    import json
    from urllib.parse import urlparse
    debug_log_path = '/Users/shifrawilliams/Documents/Repos/trender/.cursor/debug.log'
    
    # Check for multiple DATABASE_URL variants
    db_env_vars = {
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'DATABASE_PRIVATE_URL': os.getenv('DATABASE_PRIVATE_URL'),
        'DATABASE_URL_VPC': os.getenv('DATABASE_URL_VPC'),
        'DATABASE_PUBLIC_URL': os.getenv('DATABASE_PUBLIC_URL'),
        'RENDER_INSTANCE_ID': os.getenv('RENDER_INSTANCE_ID'),
        'RENDER_SERVICE_NAME': os.getenv('RENDER_SERVICE_NAME'),
    }
    
    # Mask and log all available DB URLs
    masked_vars = {}
    for key, value in db_env_vars.items():
        if value and key.startswith('DATABASE'):
            try:
                parsed = urlparse(value)
                masked_vars[key] = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
            except:
                masked_vars[key] = "parse_error"
        else:
            masked_vars[key] = "not_set" if value is None else "set"
    
    try:
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"connections.py:15","message":"Environment check - DB URLs","data":masked_vars,"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H6"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    # Validate GitHub token
    github_access_token = os.getenv('GITHUB_ACCESS_TOKEN')
    if not github_access_token:
        raise ValueError("GITHUB_ACCESS_TOKEN environment variable is required")
    
    if not github_access_token.startswith(('ghp_', 'gho_', 'github_pat_')):
        raise ValueError("GITHUB_ACCESS_TOKEN appears invalid (wrong format)")
    
    # Initialize GitHub API client
    try:
        github_api = GitHubAPIClient(access_token=github_access_token)
        await github_api.__aenter__()
    except Exception as e:
        raise ConnectionError(f"Failed to initialize GitHub API client: {e}")
    
    # Validate database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # #region agent log
    try:
        parsed = urlparse(database_url)
        masked_url = f"{parsed.scheme}://{parsed.username}:***@{parsed.hostname}:{parsed.port}{parsed.path}"
        
        # Determine if this is a VPC (private) or public IP
        hostname = parsed.hostname or ""
        is_vpc = hostname.startswith('10.') or hostname.startswith('172.16.') or hostname.startswith('192.168.')
        
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps({"location":"connections.py:70","message":"Selected DATABASE_URL for connection","data":{"masked_url":masked_url,"hostname":hostname,"port":parsed.port,"is_vpc_ip":is_vpc},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H1,H2,H3,H6"}) + '\n')
    except Exception:
        pass
    # #endregion
    
    # Initialize database connection pool with retry logic
    pool_size_min = int(os.getenv('DATABASE_POOL_MIN_SIZE', '2'))  # Reduced from 5
    pool_size_max = int(os.getenv('DATABASE_POOL_MAX_SIZE', '10'))  # Reduced from 20
    
    max_retries = 3
    for attempt in range(max_retries):
        # #region agent log
        try:
            with open(debug_log_path, 'a') as f:
                f.write(json.dumps({"location":"connections.py:60","message":"DB pool creation attempt","data":{"attempt":attempt+1,"max_retries":max_retries,"pool_size_min":pool_size_min,"pool_size_max":pool_size_max},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H2,H5"}) + '\n')
        except Exception:
            pass
        # #endregion
        
        try:
            db_pool = await asyncpg.create_pool(
                database_url,
                min_size=pool_size_min,
                max_size=pool_size_max,
                timeout=30,  # 30 second connection timeout
                command_timeout=60  # 60 second query timeout
            )
            
            # Test connection
            async with db_pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            
            return github_api, db_pool
            
        except asyncpg.InvalidPasswordError:
            raise ConnectionError("Database authentication failed (wrong password)")
        except asyncpg.InvalidCatalogNameError:
            raise ConnectionError("Database does not exist")
        except asyncpg.CannotConnectNowError:
            # #region agent log
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"location":"connections.py:76","message":"CannotConnectNowError caught","data":{"attempt":attempt+1,"will_retry":attempt<max_retries-1},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H2,H5"}) + '\n')
            except Exception:
                pass
            # #endregion
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise ConnectionError("Database connection refused (server not accepting connections)")
        except Exception as e:
            # #region agent log
            try:
                with open(debug_log_path, 'a') as f:
                    f.write(json.dumps({"location":"connections.py:86","message":"Generic exception during pool creation","data":{"attempt":attempt+1,"exception_type":type(e).__name__,"exception_msg":str(e),"will_retry":attempt<max_retries-1},"timestamp":int(__import__('time').time()*1000),"sessionId":"debug-session","hypothesisId":"H2,H3,H5"}) + '\n')
            except Exception:
                pass
            # #endregion
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise ConnectionError(f"Failed to create database connection pool: {e}")
    
    raise ConnectionError("Failed to connect after 3 attempts")


async def cleanup_connections(github_api: GitHubAPIClient, db_pool: asyncpg.Pool):
    """
    Clean up shared resources.

    Args:
        github_api: GitHub API client instance
        db_pool: Database connection pool
    """
    if github_api:
        await github_api.close()

    if db_pool:
        await db_pool.close()
