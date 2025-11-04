# CLI Commands

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

### Shell Integration

#### `crux shell-env`
Export secrets as shell environment variables.
```bash
# Load all secrets into current shell
eval $(crux shell-env)

# Load secrets with prefix
eval $(crux shell-env database/)

# Different shell formats
eval $(crux shell-env --format bash)   # default
eval $(crux shell-env --format fish)
eval $(crux shell-env --format powershell)

# Verify loaded
echo $DATABASE_PASSWORD
```

**Output example:**
```bash
export DATABASE_PASSWORD="secret123"
export API_KEY="abc123"
export STRIPE_KEY="sk_live_..."
```

#### `crux unset-env`
Remove secrets from environment.
```bash
# Unset all secrets
eval $(crux unset-env)

# Unset by prefix
eval $(crux unset-env database/)

# Unset by tag
eval $(crux unset-env --tag production)

# Different shells
eval $(crux unset-env --format fish)
```

**Use case - switch environments:**
```bash
# Load production secrets
eval $(crux shell-env --tag production)

# Done with prod, clean up
eval $(crux unset-env --tag production)

# Load dev secrets
eval $(crux shell-env --tag development)
```

### Security Scanning

#### `crux scan`
Detect hardcoded secrets in your codebase.
```bash
# Scan current directory
crux scan .

# Scan specific path
crux scan src/

# Scan single file
crux scan config.py
```

**What it detects:**
- API keys and tokens
- Passwords in code
- Private keys
- AWS credentials
- Database connection strings
- JWT tokens

**Example output:**
```
⚠ Potential secrets found:
config.py:12 - Possible API Key
utils.py:45 - Possible Password
.env.backup:3 - AWS Access Key
```

### Variable Expansion

CruxVault supports dynamic variable expansion using `${VAR}` syntax. Variables are resolved at read-time, so updates automatically propagate.
```bash
# Set base URL
crux set API_URL 'https://api.example.com'

# Reference it in other secrets
crux set USERS_ENDPOINT '${API_URL}/v1/users'
crux set POSTS_ENDPOINT '${API_URL}/v1/posts'

# Get expanded value
crux get USERS_ENDPOINT
# Output: https://api.example.com/v1/users

# Update base URL
crux set API_URL 'https://api.production.com'

# Dependent secrets automatically updated
crux get USERS_ENDPOINT
# Output: https://api.production.com/v1/users
```

**Nested expansion:**
```bash
crux set DB_HOST "localhost"
crux set DB_PORT "5432"
crux set DB_CONN 'postgresql://${DB_HOST}:${DB_PORT}'
crux set FULL_CONN '${DB_CONN}/myapp'

crux get FULL_CONN
# Output: postgresql://localhost:5432/myapp
```

**Notes:**
- Bash is notorious for exanding Vars before running the cmd, use single quotes ONLY when using Variables
- Variables expand recursively
- Circular references are detected and raise an error
- Missing variables are left as-is: `${MISSING}` stays `${MISSING}`
- Raw values stored encrypted; expansion happens on read