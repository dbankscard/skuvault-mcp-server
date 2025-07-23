# SkuVault MCP Server - Quick Start Guide

## 🚀 Setup in 3 Steps

### Step 1: Run the Setup Script

```bash
python3 setup.py
```

This will:
- Install all dependencies
- Create a `.env` file for your credentials
- Optionally configure Claude Desktop automatically

### Step 2: Add Your SkuVault Credentials

Edit the `.env` file with your SkuVault API credentials:

```bash
# Option 1: If you have tokens
SKUVAULT_TENANT_TOKEN=your_tenant_token_here
SKUVAULT_USER_TOKEN=your_user_token_here

# Option 2: Use the authenticate tool in Claude to get tokens
# Leave the above empty and use email/password when prompted
```

To get your tokens:
1. Log into SkuVault
2. Go to Settings → User Tokens
3. Copy your Tenant Token and User Token

### Step 3: Restart Claude Desktop

After setup, restart Claude Desktop to load the new server.

## ✅ Verify Installation

### Test the Server
```bash
python3 test_server.py
```

### In Claude Desktop
1. Look for "skuvault" in the MCP servers menu (🔌 icon)
2. It should show as connected

### Try Your First Command
In Claude, try:
- "Show me all warehouses in SkuVault"
- "Get product details for SKU ABC123"
- "What's the inventory for SKU XYZ789?"

## 🔧 Manual Setup (if automatic setup fails)

### 1. Install Dependencies
```bash
pip install -e .
```

### 2. Configure Claude Desktop

Add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "skuvault": {
      "command": "/usr/bin/python3",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/skuvault_mcp_server",
      "env": {
        "PYTHONPATH": "/path/to/skuvault_mcp_server",
        "SKUVAULT_TENANT_TOKEN": "your_tenant_token",
        "SKUVAULT_USER_TOKEN": "your_user_token"
      }
    }
  }
}
```

Replace:
- `/usr/bin/python3` with your Python path
- `/path/to/skuvault_mcp_server` with the actual path to this directory
- Add your actual tokens

### 3. Restart Claude Desktop

## 🆘 Troubleshooting

### Server not showing in Claude
1. Check Claude Desktop logs: Help → Toggle Developer Tools → Console
2. Verify the config file is valid JSON
3. Ensure Python path is correct: `which python3`

### Authentication errors
1. Verify your tokens are correct in `.env`
2. Try using the `authenticate` tool with email/password
3. Check if your SkuVault account has API access enabled

### Connection issues
1. Test the server: `python3 test_server.py`
2. Check your internet connection
3. Verify SkuVault API is accessible: https://app.skuvault.com/api/

## 📚 Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [PROGRESS.md](PROGRESS.md) for development details
- Explore available tools in Claude by asking "What SkuVault operations can you do?"

## 💡 Tips

1. **Safety First**: All inventory changes require confirmation
2. **Bulk Operations**: Use `get_products` with pagination for large datasets
3. **Generic Access**: Use `call_api_endpoint` for any API operation not covered by specific tools

Need help? Check the logs or create an issue on GitHub!