# Git-Like Version Control

CruxVault supports Git-like branching and commits for managing secrets across environments.

#### `crux branch`

Create and manage branches.

```bash
# Create new branch
crux branch dev

# Create from existing branch
crux branch staging --from prod

# List all branches
crux branch --list

# Delete branch
crux branch --delete staging
```

#### `crux checkout <branch>`

Switch to a different branch.

```bash
crux checkout dev
crux checkout main
```

**Note:** Switching branches replaces all secrets with the branch's committed state.

#### `crux commit`

Save current secrets state to a commit.

```bash
crux commit -m "Add production API keys"
crux commit -m "Update database credentials"
```

#### `crux status`

Show uncommitted changes.

```bash
crux status
```

**Output:**

```
On branch: dev

New secrets:
  + api/stripe_key

Modified secrets:
  M database/password

Deleted secrets:
  - temp/old_key
```

#### `crux log`

View commit history.

```bash
# Show last 10 commits
crux log

# Show more commits
crux log --limit 20

# Show history of specific branch
crux log prod
```

#### `crux diff`

Compare commits or show working tree changes.

```bash
# Show uncommitted changes
crux diff

# Compare two commit-ids
crux diff 1 3
```

#### `crux merge <branch>`

Merge another branch into current branch.

```bash
crux checkout main
crux merge dev
```

**Conflict handling:**

```bash
# If conflicts exist
Merge conflicts detected:

api/key:
  Current:  prod-key-123
  Incoming: dev-key-456

# Force accept incoming changes
crux merge dev --force
```

### Branching Workflow Example

```bash
# Setup production
crux init
crux set DATABASE_URL "prod-db"
crux set API_KEY "prod-key"
crux commit -m "Production config"

# Create dev branch
crux branch dev
crux checkout dev
crux set DATABASE_URL "dev-db"
crux set API_KEY "dev-key"
crux commit -m "Dev config"

# Switch between environments
crux checkout prod    # Use prod secrets
crux checkout dev     # Use dev secrets

# View differences
crux diff 1 2

# Merge dev changes to prod
crux checkout prod
crux merge dev
```

### Branch Strategy

**Environment-based branches:**

```bash
crux branch prod
crux branch staging
crux branch dev
```

Each branch maintains independent secret values. Use `checkout` to switch environments instantly.
