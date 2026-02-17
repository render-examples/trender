"""
Token Encryption Module

Provides symmetric encryption/decryption for GitHub OAuth tokens using Fernet (AES-128 CBC).
Encryption keys are derived from environment variables for secure secret management.

Security Features:
- Fernet encryption (AES-128 CBC with HMAC authentication)
- Base64-encoded encrypted output safe for database TEXT columns
- Automatic key generation helper for initial setup
- Support for key rotation via key_id tracking

Usage:
    from lib.encryption import encrypt_token, decrypt_token
    
    # Encrypt a token
    encrypted = encrypt_token("ghp_your_token_here", encryption_key)
    
    # Decrypt it back
    original = decrypt_token(encrypted, encryption_key)
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded encryption key suitable for environment variables
        
    Example:
        >>> key = generate_encryption_key()
        >>> print(f"GITHUB_TOKEN_ENCRYPTION_KEY={key}")
    """
    return Fernet.generate_key().decode('utf-8')


def get_encryption_key_from_env() -> Optional[bytes]:
    """
    Load encryption key from GITHUB_TOKEN_ENCRYPTION_KEY environment variable.
    
    Returns:
        Encryption key as bytes, or None if not configured
        
    Raises:
        ValueError: If key format is invalid
    """
    key_str = os.getenv('GITHUB_TOKEN_ENCRYPTION_KEY')
    if not key_str:
        return None
    
    try:
        return key_str.encode('utf-8')
    except Exception as e:
        raise ValueError(f"Invalid encryption key format: {e}")


def _get_validated_key(encryption_key: Optional[bytes]) -> bytes:
    """
    Get and validate encryption key, loading from environment if not provided.
    
    Args:
        encryption_key: Optional encryption key bytes
        
    Returns:
        Validated encryption key bytes
        
    Raises:
        ValueError: If no key is provided or found in environment
    """
    if encryption_key is None:
        encryption_key = get_encryption_key_from_env()
    
    if not encryption_key:
        raise ValueError(
            "Encryption key not provided. Set GITHUB_TOKEN_ENCRYPTION_KEY environment variable "
            "or pass encryption_key parameter."
        )
    
    return encryption_key


def encrypt_token(token: str, encryption_key: Optional[bytes] = None) -> str:
    """
    Encrypt a GitHub token using Fernet symmetric encryption.
    
    Args:
        token: The plaintext token to encrypt
        encryption_key: The encryption key (bytes). If None, loads from environment.
        
    Returns:
        Base64-encoded encrypted token (safe for database storage)
        
    Raises:
        ValueError: If encryption key is not provided or invalid
        
    Example:
        >>> encrypted = encrypt_token("ghp_abc123xyz")
        >>> assert encrypted != "ghp_abc123xyz"
        >>> assert isinstance(encrypted, str)
    """
    encryption_key = _get_validated_key(encryption_key)
    
    try:
        cipher = Fernet(encryption_key)
        token_bytes = token.encode('utf-8')
        encrypted_bytes = cipher.encrypt(token_bytes)
        return encrypted_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to encrypt token: {e}")


def decrypt_token(encrypted_token: str, encryption_key: Optional[bytes] = None) -> str:
    """
    Decrypt a GitHub token that was encrypted with encrypt_token().
    
    Args:
        encrypted_token: The Base64-encoded encrypted token from database
        encryption_key: The encryption key (bytes). If None, loads from environment.
        
    Returns:
        Decrypted plaintext token
        
    Raises:
        ValueError: If encryption key is not provided, invalid, or decryption fails
        
    Example:
        >>> encrypted = encrypt_token("ghp_abc123xyz")
        >>> decrypted = decrypt_token(encrypted)
        >>> assert decrypted == "ghp_abc123xyz"
    """
    encryption_key = _get_validated_key(encryption_key)
    
    try:
        cipher = Fernet(encryption_key)
        encrypted_bytes = encrypted_token.encode('utf-8')
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    except InvalidToken:
        raise ValueError(
            "Failed to decrypt token. The encryption key may be incorrect, "
            "or the token data may be corrupted."
        )
    except Exception as e:
        raise ValueError(f"Failed to decrypt token: {e}")


def validate_encryption_setup() -> tuple[bool, str]:
    """
    Validate that encryption is properly configured.
    
    Returns:
        Tuple of (is_valid, message)
        
    Example:
        >>> is_valid, msg = validate_encryption_setup()
        >>> if not is_valid:
        ...     print(f"Encryption setup issue: {msg}")
    """
    try:
        key = get_encryption_key_from_env()
        if not key:
            return False, "GITHUB_TOKEN_ENCRYPTION_KEY environment variable not set"
        
        # Test encryption/decryption
        test_token = "test_token_validation"
        encrypted = encrypt_token(test_token, key)
        decrypted = decrypt_token(encrypted, key)
        
        if decrypted != test_token:
            return False, "Encryption round-trip test failed"
        
        return True, "Encryption setup is valid"
    except Exception as e:
        return False, f"Encryption validation error: {e}"

