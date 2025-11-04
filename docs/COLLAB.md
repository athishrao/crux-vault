# Team Collaboration

### Workflow

**1. Setup (One person):**
```bash
# Initialize and create initial secrets
crux init
crux set DATABASE_URL "postgres://..."
crux set API_KEY "abc123"
crux commit -m "initial secrets"

# Add .cruxvault/ to git (encrypted secrets are safe to commit)
git add .cruxvault/
git commit -m "add crux secrets"
git push
```

**2. Team members clone:**
```bash
git clone <repo>
cd project

# Share master key securely (1Password, encrypted chat, etc.)
export UNIFIED_MASTER_KEY="<shared-key>"

# Verify secrets work
crux list
```

**3. Branch-based environments:**
```bash
# Developer creates feature branch
crux branch feature/new-api
crux checkout feature/new-api
crux set NEW_API_KEY "test-key"
crux commit -m "Add new API key"
git add .cruxvault/ && git commit -m "Update secrets" && git push

# Reviewer merges
git pull
crux checkout main
crux merge feature/new-api
crux commit -m "Merge feature secrets"
git add .cruxvault/ && git commit -m "Merge secrets" && git push
```

### Key Sharing Options

**Option 1: Environment variable (recommended)**
```bash
# Share once via secure channel
export UNIFIED_MASTER_KEY="base64-key"
echo 'export UNIFIED_MASTER_KEY="base64-key"' >> ~/.bashrc
```

**Option 2: 1Password/LastPass**
Store master key in team vault, team members retrieve manually.

**Option 3: CI/CD**
```yaml
# GitHub Actions
env:
  UNIFIED_MASTER_KEY: ${{ secrets.UNIFIED_MASTER_KEY }}
```

### Best Practices

- **Never commit master key** to git (`.gitignore` it)
- **Do commit `.cruxvault/` directory** (encrypted secrets are safe)
- **Use branches** for dev/staging/prod environments
- **Rotate key** when team members leave, rotation support coming soon
- **Audit log** tracks all changes with timestamps