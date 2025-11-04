# Security

### Encryption

- **Algorithm**: AES-256-GCM (Authenticated Encryption)
- **Key Storage**: System keychain via `keyring` library
- **Fallback**: Environment variable `UNIFIED_MASTER_KEY`
- **Nonce**: Random 96-bit nonce for each encryption
- **At Rest**: All secret values encrypted before storage

### Master Key Management

1. **First Priority**: System keychain (macOS Keychain, Windows Credential Manager, etc.)
2. **Second Priority**: Environment variable `UNIFIED_MASTER_KEY`
3. **Fallback**: Auto-generated key (saved to keychain if available)

```bash
# Set master key manually
export UNIFIED_MASTER_KEY="<base64-encoded-key>"
```

### Audit Logging

All operations are logged to `.cruxvault/audit.log` in JSON Lines format:

```json
{"timestamp": "2024-01-15T10:30:00", "user": "athish", "action": "set", "path": "api/key", "success": true}
{"timestamp": "2024-01-15T10:31:00", "user": "athish", "action": "get", "path": "api/key", "success": true}