#!/usr/bin/env python3
"""
Setup script for SkuVault MCP Server
"""

import os
import sys
import json
import platform
import subprocess
from pathlib import Path


def get_claude_config_path():
    """Get the Claude Desktop configuration file path based on the OS."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    else:
        raise Exception(f"Unsupported operating system: {system}")


def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        env_file.write_text(env_example.read_text())
        print("✅ Created .env file. Please edit it with your SkuVault credentials.")
        return False
    elif env_file.exists():
        print("✅ .env file already exists.")
        return True
    else:
        print("⚠️  No .env.example file found. Creating a basic .env file...")
        env_content = """# SkuVault API Credentials
SKUVAULT_TENANT_TOKEN=
SKUVAULT_USER_TOKEN=
"""
        env_file.write_text(env_content)
        print("✅ Created .env file. Please edit it with your SkuVault credentials.")
        return False


def install_dependencies():
    """Install Python dependencies."""
    print("\nChecking dependencies...")
    
    # First check if all dependencies are already installed
    try:
        import mcp
        import httpx
        import pydantic
        import dotenv
        import bs4
        print("✅ All dependencies are already installed.")
        return True
    except ImportError:
        pass
    
    print("Installing dependencies...")
    try:
        # Try installing without -e flag first
        subprocess.run([sys.executable, "-m", "pip", "install", "."], check=True)
        print("✅ Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError:
        # Fall back to manual dependency installation
        print("⚠️  Standard installation failed. Trying manual dependency installation...")
        try:
            deps = [
                '"mcp[cli]>=1.2.0"',
                "httpx>=0.25.0",
                "pydantic>=2.0.0", 
                "python-dotenv>=1.0.0",
                "beautifulsoup4>=4.12.0"
            ]
            subprocess.run([sys.executable, "-m", "pip", "install"] + deps, check=True)
            print("✅ Dependencies installed successfully.")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies.")
            print("\nPlease run manually:")
            print('  pip3 install "mcp[cli]" httpx pydantic python-dotenv beautifulsoup4')
            return False


def get_server_config():
    """Generate the server configuration for Claude Desktop."""
    cwd = os.getcwd()
    python_path = sys.executable
    
    config = {
        "mcpServers": {
            "skuvault": {
                "command": python_path,
                "args": ["-m", "src.server"],
                "cwd": cwd,
                "env": {
                    "PYTHONPATH": cwd
                }
            }
        }
    }
    
    return config


def update_claude_config():
    """Update Claude Desktop configuration."""
    config_path = get_claude_config_path()
    
    print(f"\nClaude Desktop config location: {config_path}")
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing config or create new one
    if config_path.exists():
        print("Found existing Claude Desktop configuration.")
        with open(config_path, 'r') as f:
            try:
                existing_config = json.load(f)
            except json.JSONDecodeError:
                print("⚠️  Existing config file is invalid. Creating backup...")
                backup_path = config_path.with_suffix('.backup.json')
                config_path.rename(backup_path)
                existing_config = {}
    else:
        print("No existing Claude Desktop configuration found.")
        existing_config = {}
    
    # Get new server config
    server_config = get_server_config()
    
    # Merge configurations
    if "mcpServers" not in existing_config:
        existing_config["mcpServers"] = {}
    
    if "skuvault" in existing_config["mcpServers"]:
        print("\n⚠️  SkuVault server already exists in configuration.")
        response = input("Do you want to update it? (y/n): ").lower()
        if response != 'y':
            return False
    
    existing_config["mcpServers"]["skuvault"] = server_config["mcpServers"]["skuvault"]
    
    # Save updated config
    with open(config_path, 'w') as f:
        json.dump(existing_config, f, indent=2)
    
    print("✅ Claude Desktop configuration updated successfully.")
    return True


def main():
    """Main setup function."""
    print("🚀 SkuVault MCP Server Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required.")
        print(f"   Current version: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    
    # Create .env file
    env_exists = create_env_file()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed. Please install dependencies manually.")
        sys.exit(1)
    
    # Update Claude Desktop config
    print("\n" + "=" * 50)
    print("Claude Desktop Configuration")
    print("=" * 50)
    
    response = input("\nDo you want to automatically configure Claude Desktop? (y/n): ").lower()
    
    if response == 'y':
        if update_claude_config():
            print("\n" + "=" * 50)
            print("✅ Setup completed successfully!")
            print("\nNext steps:")
            if not env_exists:
                print("1. Edit .env file with your SkuVault credentials:")
                print("   - SKUVAULT_TENANT_TOKEN=your_tenant_token")
                print("   - SKUVAULT_USER_TOKEN=your_user_token")
                print("2. Restart Claude Desktop")
            else:
                print("1. Restart Claude Desktop")
            print("3. The SkuVault server should appear in Claude's MCP menu")
        else:
            print("\n❌ Configuration update cancelled.")
    else:
        print("\nManual configuration needed. Add this to your Claude Desktop config:")
        print(json.dumps(get_server_config(), indent=2))
        print(f"\nConfig file location: {get_claude_config_path()}")
    
    print("\n" + "=" * 50)
    print("For more information, see README.md")


if __name__ == "__main__":
    main()