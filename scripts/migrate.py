#!/usr/bin/env python3
"""
Run Alembic migrations with one command.
"""
import subprocess
import sys

def run_command(cmd):
    """Run shell command."""
    print(f"➡️  Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"⚠️  {result.stderr}")
    return result.returncode

def main():
    """Main migration script."""
    print("🚀 Running Database Migrations")
    print("=" * 50)
    
    # 1. Generate migration
    message = input("📝 Migration message (or press Enter for default): ")
    if not message:
        message = "Auto-generated migration"
    
    print(f"\n📄 Generating migration: '{message}'")
    if run_command(f'alembic revision --autogenerate -m "{message}"') != 0:
        print("❌ Failed to generate migration")
        return 1
    
    # 2. Apply migration
    print("\n⬆️  Applying migration...")
    if run_command('alembic upgrade head') != 0:
        print("❌ Failed to apply migration")
        return 1
    
    print("\n✅ Migration completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())