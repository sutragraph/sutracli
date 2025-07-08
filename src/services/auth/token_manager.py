"""
Token management system for SutraKnowledge.

This module provides secure storage and retrieval of authentication tokens
for various LLM providers, particularly SuperLLM Firebase tokens.
"""

import os
import json
import base64
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class TokenManager:
    """
    Secure token storage and management for SutraKnowledge.
    
    Tokens are encrypted and stored in ~/.sutra/auth/ directory.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize token manager.
        
        Args:
            storage_dir: Custom storage directory (defaults to ~/.sutra/auth)
        """
        self.storage_dir = Path(storage_dir or Path.home() / ".sutra" / "auth")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Token file paths
        self.tokens_file = self.storage_dir / "tokens.enc"
        self.key_file = self.storage_dir / "key.dat"
        
        # Initialize encryption
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
        
        logger.debug(f"Token manager initialized with storage: {self.storage_dir}")
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for token storage."""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # Create new key based on machine-specific data
            machine_id = self._get_machine_id()
            password = machine_id.encode()
            salt = b'sutraknowledge_salt_v1'  # Fixed salt for consistency
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Save key
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            
            return key
    
    def _get_machine_id(self) -> str:
        """Get a machine-specific identifier for key generation."""
        try:
            # Try to get machine ID from various sources
            machine_sources = [
                lambda: open('/etc/machine-id', 'r').read().strip(),
                lambda: open('/var/lib/dbus/machine-id', 'r').read().strip(),
                lambda: os.popen('hostname').read().strip(),
                lambda: str(os.getuid()) + str(os.getgid()),
            ]
            
            for source in machine_sources:
                try:
                    machine_id = source()
                    if machine_id:
                        return machine_id
                except:
                    continue
            
            # Fallback to a hash of the home directory path
            return hashlib.sha256(str(Path.home()).encode()).hexdigest()[:16]
            
        except Exception:
            # Ultimate fallback
            return "sutraknowledge_default"
    
    def _load_tokens(self) -> Dict[str, Any]:
        """Load and decrypt tokens from storage."""
        if not self.tokens_file.exists():
            return {}
        
        try:
            with open(self.tokens_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.warning(f"Failed to load tokens: {e}")
            return {}
    
    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Encrypt and save tokens to storage."""
        try:
            json_data = json.dumps(tokens, indent=2)
            encrypted_data = self._cipher.encrypt(json_data.encode())
            
            with open(self.tokens_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Set restrictive permissions
            os.chmod(self.tokens_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            raise
    
    def store_token(self, provider: str, token: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store a token for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'superllm')
            token: Authentication token
            metadata: Optional metadata (expiry, user info, etc.)
        """
        tokens = self._load_tokens()
        
        token_data = {
            'token': token,
            'stored_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        tokens[provider] = token_data
        self._save_tokens(tokens)
        
        logger.info(f"Token stored for provider: {provider}")
    
    def get_token(self, provider: str) -> Optional[str]:
        """
        Retrieve a token for a specific provider.
        
        Args:
            provider: Provider name (e.g., 'superllm')
            
        Returns:
            Token string if found, None otherwise
        """
        tokens = self._load_tokens()
        
        if provider not in tokens:
            return None
        
        token_data = tokens[provider]
        
        # Check if token has expired (if expiry info is available)
        if 'metadata' in token_data and 'expires_at' in token_data['metadata']:
            try:
                expires_at = datetime.fromisoformat(token_data['metadata']['expires_at'])
                if datetime.now() > expires_at:
                    logger.warning(f"Token for {provider} has expired")
                    self.remove_token(provider)
                    return None
            except Exception:
                pass  # Ignore expiry check errors
        
        return token_data['token']
    
    def remove_token(self, provider: str) -> bool:
        """
        Remove a token for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            True if token was removed, False if not found
        """
        tokens = self._load_tokens()
        
        if provider in tokens:
            del tokens[provider]
            self._save_tokens(tokens)
            logger.info(f"Token removed for provider: {provider}")
            return True
        
        return False
    
    def list_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        List all providers with stored tokens and their metadata.
        
        Returns:
            Dictionary of provider info
        """
        tokens = self._load_tokens()
        result = {}
        
        for provider, token_data in tokens.items():
            result[provider] = {
                'stored_at': token_data.get('stored_at'),
                'metadata': token_data.get('metadata', {}),
                'has_token': bool(token_data.get('token'))
            }
        
        return result
    
    def validate_token(self, provider: str, token: str) -> bool:
        """
        Validate if a token matches the stored token for a provider.
        
        Args:
            provider: Provider name
            token: Token to validate
            
        Returns:
            True if token matches, False otherwise
        """
        stored_token = self.get_token(provider)
        return stored_token == token if stored_token else False
    
    def clear_all_tokens(self) -> None:
        """Remove all stored tokens."""
        if self.tokens_file.exists():
            self.tokens_file.unlink()
        logger.info("All tokens cleared")


# Global token manager instance
_token_manager = None


def get_token_manager() -> TokenManager:
    """Get the global token manager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager
