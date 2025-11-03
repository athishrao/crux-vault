#!/usr/bin/env python3
"""
CruxVault Python API Demo

Demonstrates all available Python API functions.
Run this after initializing a CruxVault project: `crux init`
"""

import json
import cruxvault as crux


def demo_basic_operations():
    print("=" * 60)
    print("BASIC OPERATIONS")
    print("=" * 60)
    
    print("\n1. Setting secrets...")
    crux.set("demo/api_key", "abc123xyz")
    crux.set("demo/database_password", "super-secret-pass")
    crux.set("demo/stripe_key", "sk_live_demo123", tags=["production", "payment"])
    print("✓ Set 3 secrets")
    
    print("\n2. Getting a secret...")
    api_key = crux.get("demo/api_key")
    print(f"demo/api_key = {api_key}")
    
    print("\n3. Deleting a secret...")
    crux.delete("demo/api_key")
    print("✓ Deleted demo/api_key")


def demo_listing():
    print("\n" + "=" * 60)
    print("LISTING SECRETS")
    print("=" * 60)
    
    print("\n1. List as JSON:")
    secrets = crux.list()
    print(json.dumps(secrets, indent=2))
    
    print("\n2. List with prefix 'demo/':")
    demo_secrets = crux.list(prefix="demo/")
    for secret in demo_secrets:
        print(f"  - {secret['path']} (v{secret['version']})")
    
    print("\n3. Pretty print table:")
    crux.list(print_=True)


def demo_version_control():
    print("\n" + "=" * 60)
    print("VERSION CONTROL")
    print("=" * 60)
    
    print("\n1. Creating version history...")
    crux.set("demo/versioned_key", "version1")
    crux.set("demo/versioned_key", "version2")
    crux.set("demo/versioned_key", "version3")
    print("✓ Created 3 versions")
    
    print("\n2. History as JSON:")
    history = crux.history("demo/versioned_key")
    for v in history:
        print(f"  v{v['version']}: {v['value']} ({v['created_at'][:19]})")
    
    print("\n3. Pretty print history:")
    crux.history("demo/versioned_key", print_=True)
    
    print("\n4. Rolling back to version 1...")
    crux.rollback("demo/versioned_key", version=1)
    current_value = crux.get("demo/versioned_key")
    print(f"✓ Rolled back, current value: {current_value}")


def demo_tags():
    print("\n" + "=" * 60)
    print("TAGS")
    print("=" * 60)
    
    print("\n1. Setting secrets with tags...")
    crux.set("demo/prod_key", "prod123", tags=["production"])
    crux.set("demo/staging_key", "stage123", tags=["staging"])
    crux.set("demo/payment_key", "pay123", tags=["production", "payment"])
    print("✓ Set 3 secrets with tags")
    
    print("\n2. All secrets with their tags:")
    secrets = crux.list(prefix="demo/")
    for secret in secrets:
        tags = ", ".join(secret['tags']) if secret['tags'] else "no tags"
        print(f"  {secret['path']}: [{tags}]")


def demo_class_based():
    print("\n" + "=" * 60)
    print("CLASS-BASED API")
    print("=" * 60)
    
    print("\n1. Creating CruxVault client...")
    client = crux.CruxVault()
    print("✓ Client created")
    
    print("\n2. Using client methods...")
    client.set("demo/client_key", "client-value")
    value = client.get("demo/client_key")
    print(f"Set and retrieved: {value}")
    
    secrets = client.list(prefix="demo/")
    print(f"Found {len(secrets)} secrets with 'demo/' prefix")


def demo_error_handling():
    print("\n" + "=" * 60)
    print("ERROR HANDLING")
    print("=" * 60)
    
    print("\n1. Trying to get nonexistent secret...")
    try:
        value = crux.get("nonexistent/key")
    except Exception as e:
        print(f"✓ Caught error: {type(e).__name__}: {e}")
    
    print("\n2. Trying to rollback to invalid version...")
    try:
        crux.rollback("demo/database_password", version=999)
    except Exception as e:
        print(f"✓ Caught error: {type(e).__name__}: {e}")


def demo_practical_usage():
    print("\n" + "=" * 60)
    print("PRACTICAL USAGE")
    print("=" * 60)
    
    print("\n1. Building database connection string:")
    crux.set("app/db_host", "localhost")
    crux.set("app/db_port", "5432")
    crux.set("app/db_user", "myapp")
    crux.set("app/db_password", "secret123")
    
    db_conn = (
        f"postgresql://{crux.get('app/db_user')}:"
        f"{crux.get('app/db_password')}@"
        f"{crux.get('app/db_host')}:"
        f"{crux.get('app/db_port')}/myapp"
    )
    print(f"Connection string: {db_conn}")
    
    print("\n2. Loading all secrets into dictionary:")
    secrets_dict = {}
    for secret in crux.list(prefix="app/"):
        key = secret['path'].replace('app/', '').upper()
        secrets_dict[key] = crux.get(secret['path'])
    
    print(f"Loaded {len(secrets_dict)} secrets:")
    for key in secrets_dict:
        print(f"  {key} = {secrets_dict[key]}")
    
    print("\n3. Environment-specific configuration:")
    env = "production"
    crux.set(f"config/{env}/api_url", "https://api.prod.com")
    crux.set(f"config/{env}/debug", "false")
    
    api_url = crux.get(f"config/{env}/api_url")
    debug = crux.get(f"config/{env}/debug")
    print(f"Environment: {env}")
    print(f"  API URL: {api_url}")
    print(f"  Debug: {debug}")


def cleanup():
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)
    
    print("\nDeleting all demo secrets...")
    secrets = crux.list()
    deleted = 0
    for secret in secrets:
        if secret['path'].startswith('demo/') or secret['path'].startswith('app/') or secret['path'].startswith('config/'):
            crux.delete(secret['path'])
            deleted += 1
    
    print(f"✓ Deleted {deleted} demo secrets")


def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "CRUXVAULT PYTHON API DEMO" + " " * 15 + "   ║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        demo_basic_operations()
        demo_listing()
        demo_version_control()
        demo_tags()
        demo_class_based()
        demo_error_handling()
        demo_practical_usage()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE!")
        print("=" * 60)
        
        response = input("\nDelete demo secrets? (y/N): ")
        if response.lower() == 'y':
            cleanup()
        
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        print("\nMake sure you've initialized crux:")
        print("  crux init")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

