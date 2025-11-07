# Python API

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

# Load to Python os env
crux.load_crux_secrets("database/") # can then use as os.environ.get("database/password")
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
| `load_crux_secrets(path)`         | Load to pytho os env  | `None`                 |
