"""
Data encryption service for pharmaceutical data security.

Provides AES-256-GCM encryption for sensitive API response data,
key management, and secure data handling for regulatory compliance.

Version: 1.0.0
Author: CognitoAI Development Team
"""

import base64
import hashlib
import json
import os
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import structlog

logger = structlog.get_logger(__name__)


class DataEncryptionService:
    """
    Encryption service for pharmaceutical data protection.

    Implements AES-256-GCM encryption with secure key derivation
    and data integrity verification for HIPAA/FDA compliance.

    Since:
        Version 1.0.0
    """

    def __init__(
        self,
        master_key: Optional[str] = None,
        key_rotation_enabled: bool = True
    ):
        """
        Initialize encryption service.

        Args:
            master_key: Master encryption key (from environment)
            key_rotation_enabled: Enable automatic key rotation

        Since:
            Version 1.0.0
        """
        self.master_key = master_key or os.environ.get('PHARMA_ENCRYPTION_KEY')
        if not self.master_key:
            raise ValueError("Encryption master key not configured")

        self.key_rotation_enabled = key_rotation_enabled
        self._validate_key_strength()

    def _validate_key_strength(self):
        """
        Validate encryption key meets security requirements.

        Since:
            Version 1.0.0
        """
        if len(self.master_key) < 32:
            raise ValueError(
                "Master key must be at least 256 bits for pharmaceutical compliance"
            )

    def _derive_key(self, salt: bytes, info: bytes = b'') -> bytes:
        """
        Derive encryption key using PBKDF2.

        Args:
            salt: Random salt for key derivation
            info: Additional context for key derivation

        Returns:
            Derived 256-bit key

        Since:
            Version 1.0.0
        """
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(self.master_key.encode() + info)

    async def encrypt_data(
        self,
        data: Dict[str, Any],
        context: str = "api_response"
    ) -> Dict[str, Any]:
        """
        Encrypt sensitive pharmaceutical data.

        Args:
            data: Data to encrypt
            context: Encryption context for key derivation

        Returns:
            Encrypted data with metadata

        Since:
            Version 1.0.0
        """
        try:
            # Serialize data
            plaintext = json.dumps(data, sort_keys=True).encode()

            # Generate encryption parameters
            salt = os.urandom(16)
            nonce = os.urandom(12)

            # Derive key with context
            key = self._derive_key(salt, context.encode())

            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()

            # Create encrypted payload
            encrypted_data = {
                'encrypted': True,
                'algorithm': 'AES-256-GCM',
                'version': '1.0',
                'context': context,
                'salt': base64.b64encode(salt).decode(),
                'nonce': base64.b64encode(nonce).decode(),
                'ciphertext': base64.b64encode(ciphertext).decode(),
                'tag': base64.b64encode(encryptor.tag).decode()
            }

            logger.info(
                "Data encrypted successfully",
                context=context,
                size=len(plaintext)
            )

            return encrypted_data

        except Exception as e:
            logger.error(
                "Encryption failed",
                error=str(e),
                context=context
            )
            raise

    async def decrypt_data(
        self,
        encrypted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decrypt encrypted pharmaceutical data.

        Args:
            encrypted_data: Encrypted data payload

        Returns:
            Decrypted original data

        Since:
            Version 1.0.0
        """
        try:
            if not encrypted_data.get('encrypted'):
                return encrypted_data

            # Extract encryption parameters
            salt = base64.b64decode(encrypted_data['salt'])
            nonce = base64.b64decode(encrypted_data['nonce'])
            ciphertext = base64.b64decode(encrypted_data['ciphertext'])
            tag = base64.b64decode(encrypted_data['tag'])
            context = encrypted_data.get('context', 'api_response')

            # Derive key
            key = self._derive_key(salt, context.encode())

            # Decrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # Deserialize data
            data = json.loads(plaintext.decode())

            logger.info(
                "Data decrypted successfully",
                context=context
            )

            return data

        except Exception as e:
            logger.error(
                "Decryption failed",
                error=str(e)
            )
            raise

    async def encrypt_field(
        self,
        value: str,
        field_name: str
    ) -> str:
        """
        Encrypt individual field value.

        Args:
            value: Field value to encrypt
            field_name: Name of field for context

        Returns:
            Encrypted field value as base64 string

        Since:
            Version 1.0.0
        """
        encrypted = await self.encrypt_data(
            {'value': value},
            context=f"field_{field_name}"
        )
        return base64.b64encode(
            json.dumps(encrypted).encode()
        ).decode()

    async def decrypt_field(
        self,
        encrypted_value: str
    ) -> str:
        """
        Decrypt individual field value.

        Args:
            encrypted_value: Base64 encoded encrypted value

        Returns:
            Decrypted field value

        Since:
            Version 1.0.0
        """
        encrypted_data = json.loads(
            base64.b64decode(encrypted_value).decode()
        )
        decrypted = await self.decrypt_data(encrypted_data)
        return decrypted['value']

    def generate_hmac(
        self,
        data: str,
        key: Optional[bytes] = None
    ) -> str:
        """
        Generate HMAC for data integrity verification.

        Args:
            data: Data to generate HMAC for
            key: Optional HMAC key

        Returns:
            HMAC hex digest

        Since:
            Version 1.0.0
        """
        if key is None:
            key = hashlib.sha256(self.master_key.encode()).digest()

        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(data.encode())
        return h.finalize().hex()

    def verify_hmac(
        self,
        data: str,
        expected_hmac: str,
        key: Optional[bytes] = None
    ) -> bool:
        """
        Verify HMAC for data integrity.

        Args:
            data: Data to verify
            expected_hmac: Expected HMAC value
            key: Optional HMAC key

        Returns:
            True if HMAC matches

        Since:
            Version 1.0.0
        """
        calculated = self.generate_hmac(data, key)
        return calculated == expected_hmac

    async def rotate_encryption_key(
        self,
        new_master_key: str
    ) -> Dict[str, Any]:
        """
        Rotate master encryption key.

        Args:
            new_master_key: New master key

        Returns:
            Rotation metadata

        Since:
            Version 1.0.0
        """
        if not self.key_rotation_enabled:
            raise ValueError("Key rotation is disabled")

        # Validate new key
        if len(new_master_key) < 32:
            raise ValueError("New key does not meet security requirements")

        old_key = self.master_key
        rotation_id = str(os.urandom(8).hex())

        try:
            # Update master key
            self.master_key = new_master_key
            self._validate_key_strength()

            logger.info(
                "Encryption key rotated",
                rotation_id=rotation_id
            )

            return {
                'rotation_id': rotation_id,
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat(),
                'algorithm': 'AES-256-GCM'
            }

        except Exception as e:
            # Rollback on failure
            self.master_key = old_key
            logger.error(
                "Key rotation failed",
                error=str(e),
                rotation_id=rotation_id
            )
            raise


class DataMaskingService:
    """
    Data masking service for non-authorized access.

    Provides field-level masking for sensitive pharmaceutical
    data when accessed by users without full authorization.

    Since:
        Version 1.0.0
    """

    def __init__(self, masking_rules: Optional[Dict[str, str]] = None):
        """
        Initialize data masking service.

        Args:
            masking_rules: Custom masking rules by field

        Since:
            Version 1.0.0
        """
        self.masking_rules = masking_rules or self._default_rules()

    def _default_rules(self) -> Dict[str, str]:
        """
        Get default masking rules for pharmaceutical data.

        Returns:
            Default masking configuration

        Since:
            Version 1.0.0
        """
        return {
            'patient_id': 'hash',
            'patient_name': 'redact',
            'ssn': 'partial',
            'dob': 'year_only',
            'email': 'partial_email',
            'phone': 'partial_phone',
            'address': 'city_state_only',
            'prescription_id': 'hash',
            'physician_dea': 'redact',
            'clinical_notes': 'redact_pii'
        }

    async def mask_data(
        self,
        data: Dict[str, Any],
        user_role: str = 'viewer'
    ) -> Dict[str, Any]:
        """
        Mask sensitive fields based on user role.

        Args:
            data: Data to mask
            user_role: User's authorization level

        Returns:
            Masked data

        Since:
            Version 1.0.0
        """
        if user_role == 'admin':
            return data  # Full access

        masked_data = data.copy()

        for field, value in data.items():
            if field in self.masking_rules:
                rule = self.masking_rules[field]
                masked_data[field] = self._apply_mask(value, rule)

        return masked_data

    def _apply_mask(self, value: Any, rule: str) -> Any:
        """
        Apply masking rule to value.

        Args:
            value: Value to mask
            rule: Masking rule type

        Returns:
            Masked value

        Since:
            Version 1.0.0
        """
        if value is None:
            return None

        if rule == 'redact':
            return '***REDACTED***'
        elif rule == 'hash':
            return hashlib.sha256(str(value).encode()).hexdigest()[:8]
        elif rule == 'partial':
            s = str(value)
            if len(s) > 4:
                return f"{s[:2]}{'*' * (len(s)-4)}{s[-2:]}"
            return '*' * len(s)
        elif rule == 'partial_email' and '@' in str(value):
            parts = str(value).split('@')
            return f"{parts[0][:2]}***@{parts[1]}"
        elif rule == 'partial_phone':
            s = ''.join(c for c in str(value) if c.isdigit())
            if len(s) >= 10:
                return f"***-***-{s[-4:]}"
            return '***-****'

        return '***MASKED***'