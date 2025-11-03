# CruxVault

CruxVault is a developer-first tool for managing secrets, configs, and feature flags, basically everything you don’t want leaking to the internet. Built with Python, it encrypts your data with AES-256-GCM (because “just trust me” is not a security strategy), keeps version history so you can undo your mistakes!
Whether you’re wrangling local dev secrets or juggling production chaos, CruxVault keeps your sensitive data safe, consistent, and slightly less terrifying!
Available in 2 flavors - `CruxVault CLI` and `CruxVault Python API`

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **AES-256-GCM Encryption** - Military-grade encryption for all secrets at rest
- **Local SQLite Storage** - Fast, reliable, offline-first storage
- **Version History** - Track changes and rollback to any previous version
- **Tags & Organization** - Organize secrets with tags and hierarchical paths
- **Audit Logging** - Comprehensive audit trail of all operations
- **System Keychain Integration** - Secure master key storage
- **Git-like Interface** - Intuitive commands that feel natural
- **Development Mode** - Generate fake secrets for local development
- **Import/Export** - Work with .env files seamlessly

## Installation

### From Source

```bash
git clone https://github.com/athishrao/crux-vault.git
cd crux-vault
```

#### Using Editable Pip
```bash
pip install -e .
````

#### Using Poetry
```bash
poetry install
poetry shell
```

### Pip Install from Git

```bash
pip install git+https://github.com/athishrao/crux-vault.git
```

Alternatively, add this to your requirements.txt

```bash
crux @ git+https://github.com/athishrao/crux-vault.git
```

## CLI Commands

### Core Commands

#### `crux init`

Initialize Cruxvalt in the current directory. Creates `.cruxvalt/` directory with configuration and storage.

```bash
crux init
```

#### `crux set <path> <value>`

Set a secret value. Creates a new secret or updates an existing one.

```bash
# Basic usage
crux set api/key "abc123"

# With tags
crux set stripe/key "sk_test_..." --tag production --tag payment

# Different types
crux set database/host "localhost" --type config
crux set feature/new_ui "true" --type flag

# JSON output
crux set api/key "value" --json
```

#### `crux get <path>`

Retrieve a secret value.

```bash
# Basic usage
crux get database/password

# JSON output
crux get database/password --json

# Quiet mode (for piping)
crux get database/password --quiet | pbcopy
```

#### `crux list [path]`

List all secrets, optionally filtered by path prefix.

```bash
# List all secrets
crux list

# Filter by prefix
crux list database/

# Show actual values (hidden by default)
crux list --show-values

# JSON output
crux list --json
```

#### `crux delete <path>`

Delete a secret.

```bash
# With confirmation
crux delete temp/key

# Skip confirmation
crux delete temp/key --force
```

#### `crux history <path>`

Show version history for a secret.

```bash
# View history
crux history api/key

# JSON output
crux history api/key --json
```

#### `crux rollback <path> <version>`

Rollback a secret to a previous version.

```bash
# With confirmation
crux rollback api/key 1

# Skip confirmation
crux rollback api/key 1 --force
```

### Development Commands

#### `crux dev start`

Generate fake secrets for local development.

```bash
# Generate 10 fake secrets (default)
crux dev start

# Generate custom number
crux dev start --count 20
```

#### `crux dev export`

Export all secrets as a .env file.

```bash
# Output to stdout
crux dev export

# Save to file
crux dev export --output .env.local

# Pipe to clipboard
crux dev export | pbcopy
```

### Import/Export

#### `crux import-env <file>`

Import secrets from a .env file.

```bash
# Basic import
crux import-env .env.production

# Import with prefix
crux import-env .env.staging --prefix staging
```

## Python API

Use CruxVault programmatically in your Python applications.

### Installation

```bash
pip install git+https://github.com/athishrao/crux-vault.git
```

### Quick Start

```python
import cruxvault as crux

# Initialize (first time only)
crux.init()

# Set secrets
crux.set("database/password", "secret123")
crux.set("stripe/key", "sk_live_...", tags=["production", "payment"])

# Get secrets
password = crux.get("database/password")
print(password)  # "secret123"

# List secrets (returns JSON)
secrets = crux.list()
for secret in secrets:
    print(f"{secret['path']}: v{secret['version']}")

# Pretty print
crux.list(pretty=True)  # Rich table output

# Delete secrets
crux.delete("temp/key")
```

### Class-Based API

```python
from cruxvault import CruxVault

# Initialize client
client = CruxVault()

# All operations
client.set("api/key", "value", tags=["dev"])
value = client.get("api/key")
secrets = client.list(prefix="api/")
client.delete("api/key")

# Version control
history = client.history("api/key")
client.rollback("api/key", version=1)
```

### Integration Examples

**Django settings.py:**

```python
import cruxvault as crux

SECRET_KEY = crux.get("django/secret_key")
DATABASE_PASSWORD = crux.get("database/password")
STRIPE_KEY = crux.get("stripe/secret_key")
```

**Flask app:**

```python
from flask import Flask
import cruxvault as crux

app = Flask(__name__)
app.config['DATABASE_URI'] = f"postgresql://user:{crux.get('db/password')}@localhost/db"
```

**Environment variables:**

```python
import os
import cruxvault as crux

# Load all secrets into environment
for secret in crux.list():
    env_var = secret['path'].upper().replace('/', '_')
    os.environ[env_var] = crux.get(secret['path'])
```

### Error Handling

```python
try:
    value = crux.get("nonexistent/key")
except FileNotFoundError:
    print("Secret not found")
except Exception as e:
    print(f"Error: {e}")
```

### API Reference

| Method                            | Description           | Returns                |
| --------------------------------- | --------------------- | ---------------------- |
| `get(path)`                       | Retrieve secret value | `str`                  |
| `set(path, value, tags=[])`       | Store/update secret   | `None`                 |
| `delete(path)`                    | Delete secret         | `bool`                 |
| `list(prefix=None, pretty=False)` | List secrets          | `list[dict]` or `None` |
| `history(path)`                   | Get version history   | `list[dict]`           |
| `rollback(path, version)`         | Restore old version   | `None`                 |

## Security

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
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_crypto.py
```

## Planned Features

### Team Collaboration

Crux secrets live in your git repo, encrypted. Your team
uses git for syncing, just like code.
Wrong merges in case of conflicts should not be an issue, history intact - easily revertable.

1. One person: `crux init --shared && crux keygen > team.key`
2. Share team.key securely (1Password, etc.)
3. Everyone: `crux import-key team.key`
4. Use git normally: commit, push, pull

That's it. No servers, no accounts, no new workflows.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions:

- Open an issue on GitHub
- Review test files for examples
