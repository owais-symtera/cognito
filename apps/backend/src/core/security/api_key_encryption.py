"""
API Key Encryption Service for secure storage.

Provides encryption and decryption of API keys at rest using
industry-standard encryption with key rotation support.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import os
import base64
import hashlib
import json
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import structlog

logger = structlog.get_logger(__name__)


class APIKeyEncryption:
    """
    Manages encryption and decryption of API keys.

    Provides secure storage of sensitive API keys with encryption at rest,
    key rotation, and audit logging for pharmaceutical compliance.

    Example:
        >>> encryption = APIKeyEncryption()
        >>> encrypted = encryption.encrypt_api_key("sk-secret-key", "openai")
        >>> decrypted = encryption.decrypt_api_key(encrypted, "openai")

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        master_key: Optional[str] = None,
        key_rotation_days: int = 90,
        enable_audit: bool = True
    ):
        """
        Initialize API key encryption service.

        Args:
            master_key: Master encryption key (loads from env if not provided)
            key_rotation_days: Days between key rotations
            enable_audit: Enable audit logging of key operations

        Since:
            Version 1.0.0
        """
        self.master_key = master_key or os.getenv('ENCRYPTION_MASTER_KEY')
        if not self.master_key:
            # Generate a new master key if not provided
            self.master_key = self._generate_master_key()
            logger.warning("Generated new master key. Store in ENCRYPTION_MASTER_KEY env var.")

        self.key_rotation_days = key_rotation_days
        self.enable_audit = enable_audit
        self.cipher_suite = self._create_cipher_suite()
        self.key_metadata: Dict[str, Any] = {}
        self._load_key_metadata()

    def _generate_master_key(self) -> str:
        """
        Generate a new master encryption key.

        Returns:
            Base64 encoded master key

        Since:
            Version 1.0.0
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()

    def _create_cipher_suite(self) -> Fernet:
        """
        Create cipher suite from master key.

        Returns:
            Fernet cipher suite

        Since:
            Version 1.0.0
        """
        # Derive encryption key from master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'pharmaceutical_intelligence_salt',  # Should be random in production
            iterations=100000,
            backend=default_backend()
        )

        key_bytes = self.master_key.encode() if isinstance(self.master_key, str) else self.master_key
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes[:32]))
        return Fernet(derived_key)

    def encrypt_api_key(
        self,
        api_key: str,
        provider: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Encrypt an API key for secure storage.

        Args:
            api_key: Plain text API key
            provider: Provider name (e.g., 'openai', 'anthropic')
            metadata: Optional metadata about the key

        Returns:
            Encrypted API key string

        Since:
            Version 1.0.0
        """
        try:
            # Create key payload with metadata
            payload = {
                'key': api_key,
                'provider': provider,
                'encrypted_at': datetime.utcnow().isoformat(),
                'metadata': metadata or {}
            }

            # Serialize and encrypt
            payload_bytes = json.dumps(payload).encode()
            encrypted = self.cipher_suite.encrypt(payload_bytes)
            encrypted_str = base64.urlsafe_b64encode(encrypted).decode()

            # Update key metadata
            self._update_key_metadata(provider, encrypted_str)

            # Audit log
            if self.enable_audit:
                self._audit_log('encrypt', provider, success=True)

            logger.info(f"API key encrypted for provider: {provider}")
            return encrypted_str

        except Exception as e:
            logger.error(f"Failed to encrypt API key for {provider}: {e}")
            if self.enable_audit:
                self._audit_log('encrypt', provider, success=False, error=str(e))
            raise

    def decrypt_api_key(
        self,
        encrypted_key: str,
        provider: str
    ) -> str:
        """
        Decrypt an API key for use.

        Args:
            encrypted_key: Encrypted API key string
            provider: Provider name

        Returns:
            Decrypted API key

        Since:
            Version 1.0.0
        """
        try:
            # Decode and decrypt
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted_bytes = self.cipher_suite.decrypt(encrypted_bytes)

            # Parse payload
            payload = json.loads(decrypted_bytes.decode())

            # Verify provider matches
            if payload['provider'] != provider:
                raise ValueError(f"Provider mismatch: expected {provider}, got {payload['provider']}")

            # Check if key needs rotation
            encrypted_at = datetime.fromisoformat(payload['encrypted_at'])
            if self._needs_rotation(encrypted_at):
                logger.warning(f"API key for {provider} needs rotation (encrypted {encrypted_at})")

            # Audit log
            if self.enable_audit:
                self._audit_log('decrypt', provider, success=True)

            return payload['key']

        except Exception as e:
            logger.error(f"Failed to decrypt API key for {provider}: {e}")
            if self.enable_audit:
                self._audit_log('decrypt', provider, success=False, error=str(e))
            raise

    def rotate_key(
        self,
        old_encrypted_key: str,
        provider: str,
        new_api_key: Optional[str] = None
    ) -> str:
        """
        Rotate an API key with a new encryption.

        Args:
            old_encrypted_key: Current encrypted key
            provider: Provider name
            new_api_key: New API key (if changed), otherwise re-encrypts existing

        Returns:
            New encrypted key

        Since:
            Version 1.0.0
        """
        try:
            # Decrypt old key
            if new_api_key is None:
                new_api_key = self.decrypt_api_key(old_encrypted_key, provider)

            # Re-encrypt with new timestamp
            new_encrypted = self.encrypt_api_key(
                new_api_key,
                provider,
                metadata={'rotated': True, 'rotation_date': datetime.utcnow().isoformat()}
            )

            # Audit log
            if self.enable_audit:
                self._audit_log('rotate', provider, success=True)

            logger.info(f"API key rotated for provider: {provider}")
            return new_encrypted

        except Exception as e:
            logger.error(f"Failed to rotate API key for {provider}: {e}")
            if self.enable_audit:
                self._audit_log('rotate', provider, success=False, error=str(e))
            raise

    def batch_encrypt_keys(
        self,
        api_keys: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Encrypt multiple API keys in batch.

        Args:
            api_keys: Dictionary of provider -> api_key

        Returns:
            Dictionary of provider -> encrypted_key

        Since:
            Version 1.0.0
        """
        encrypted_keys = {}

        for provider, api_key in api_keys.items():
            if api_key:  # Skip empty keys
                try:
                    encrypted_keys[provider] = self.encrypt_api_key(api_key, provider)
                except Exception as e:
                    logger.error(f"Failed to encrypt key for {provider}: {e}")
                    encrypted_keys[provider] = None

        return encrypted_keys

    def batch_decrypt_keys(
        self,
        encrypted_keys: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Decrypt multiple API keys in batch.

        Args:
            encrypted_keys: Dictionary of provider -> encrypted_key

        Returns:
            Dictionary of provider -> api_key

        Since:
            Version 1.0.0
        """
        decrypted_keys = {}

        for provider, encrypted_key in encrypted_keys.items():
            if encrypted_key:  # Skip empty keys
                try:
                    decrypted_keys[provider] = self.decrypt_api_key(encrypted_key, provider)
                except Exception as e:
                    logger.error(f"Failed to decrypt key for {provider}: {e}")
                    decrypted_keys[provider] = None

        return decrypted_keys

    def _needs_rotation(self, encrypted_at: datetime) -> bool:
        """
        Check if a key needs rotation.

        Args:
            encrypted_at: When the key was encrypted

        Returns:
            True if rotation needed

        Since:
            Version 1.0.0
        """
        rotation_threshold = datetime.utcnow() - timedelta(days=self.key_rotation_days)
        return encrypted_at < rotation_threshold

    def _update_key_metadata(self, provider: str, encrypted_key: str):
        """
        Update metadata for encrypted key.

        Args:
            provider: Provider name
            encrypted_key: Encrypted key string

        Since:
            Version 1.0.0
        """
        self.key_metadata[provider] = {
            'encrypted_at': datetime.utcnow().isoformat(),
            'key_hash': hashlib.sha256(encrypted_key.encode()).hexdigest()[:16],
            'rotation_due': (datetime.utcnow() + timedelta(days=self.key_rotation_days)).isoformat()
        }

        self._save_key_metadata()

    def _load_key_metadata(self):
        """
        Load key metadata from storage.

        Since:
            Version 1.0.0
        """
        metadata_file = os.getenv('KEY_METADATA_FILE', '.key_metadata.json')
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    self.key_metadata = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load key metadata: {e}")
                self.key_metadata = {}

    def _save_key_metadata(self):
        """
        Save key metadata to storage.

        Since:
            Version 1.0.0
        """
        metadata_file = os.getenv('KEY_METADATA_FILE', '.key_metadata.json')
        try:
            with open(metadata_file, 'w') as f:
                json.dump(self.key_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save key metadata: {e}")

    def _audit_log(
        self,
        operation: str,
        provider: str,
        success: bool,
        error: Optional[str] = None
    ):
        """
        Log key operation for audit trail.

        Args:
            operation: Operation type (encrypt, decrypt, rotate)
            provider: Provider name
            success: Whether operation succeeded
            error: Error message if failed

        Since:
            Version 1.0.0
        """
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'provider': provider,
            'success': success,
            'error': error,
            'user': os.getenv('USER', 'system')
        }

        # In production, this would write to secure audit log
        logger.info("API key operation audit", **audit_entry)

    def get_rotation_status(self) -> Dict[str, Any]:
        """
        Get rotation status for all keys.

        Returns:
            Dictionary with rotation information

        Since:
            Version 1.0.0
        """
        status = {}

        for provider, metadata in self.key_metadata.items():
            encrypted_at = datetime.fromisoformat(metadata['encrypted_at'])
            rotation_due = datetime.fromisoformat(metadata['rotation_due'])

            status[provider] = {
                'encrypted_at': metadata['encrypted_at'],
                'rotation_due': metadata['rotation_due'],
                'needs_rotation': datetime.utcnow() > rotation_due,
                'days_until_rotation': max(0, (rotation_due - datetime.utcnow()).days)
            }

        return status

    def validate_encryption(self) -> Dict[str, bool]:
        """
        Validate encryption is working correctly.

        Returns:
            Validation status for each provider

        Since:
            Version 1.0.0
        """
        test_keys = {
            'test_provider': 'test_api_key_123'
        }

        validation = {}

        for provider, test_key in test_keys.items():
            try:
                # Test encrypt/decrypt cycle
                encrypted = self.encrypt_api_key(test_key, provider)
                decrypted = self.decrypt_api_key(encrypted, provider)

                validation[provider] = decrypted == test_key

            except Exception as e:
                logger.error(f"Validation failed for {provider}: {e}")
                validation[provider] = False

        return validation


# Global instance
api_key_encryption = APIKeyEncryption()


def get_api_key_encryption() -> APIKeyEncryption:
    """
    Get global API key encryption instance.

    Returns:
        APIKeyEncryption instance

    Since:
        Version 1.0.0
    """
    return api_key_encryption