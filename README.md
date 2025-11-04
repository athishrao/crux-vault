# CruxVault

CruxVault is a developer-first, git-like tool for managing secrets, configs, and feature flags, basically everything you don’t want leaking to the internet. Built with Python, it encrypts your data with AES-256-GCM, keeps version history so you can undo your mistakes!

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

[Installation Doc](docs/INSTALLATION.md)

## CLI Commands

[CLI Commands Doc](docs/CLI.md)

[Git Style CLI Commands Doc](docs/GIT_LIKE.md)

## Python API

[Python API Doc](docs/PYTHON_API.md)

## Security

[Security Doc](docs/SECURITY.md)

## Testing

[Testing Doc](docs/TEST.md)

## Team Collaboration

### Best Practices and Notes

- **Never commit master key** to git (`.gitignore` it)
- **Do commit `.cruxvault/` directory** (encrypted secrets are safe)
- **Use branches** for dev/staging/prod environments
- **Rotate key** when team members leave, rotation support coming soon
- **Audit log** tracks all changes with timestamps

[Team Collaboration Doc](docs/COLLAB.md)

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
