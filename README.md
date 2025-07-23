# SkuVault MCP Server

A Model Context Protocol (MCP) server that provides seamless integration with the SkuVault inventory management system API. Built for production use with enterprise-grade features.

## 🚀 Features

### Core Functionality
- **Product Management**: Create, read, update products individually or in batches
- **Inventory Control**: Add, remove, and set inventory quantities across warehouses
- **Warehouse Operations**: List warehouses and manage inventory by location
- **Smart Analytics**: Active/inactive products, low stock alerts, inventory summaries

### Production-Ready
- ✅ **Rate Limiting**: Dynamic rate limit learning with exponential backoff
- ✅ **Caching**: Intelligent response caching to minimize API calls
- ✅ **Safety**: Confirmation requirements for all mutating operations
- ✅ **Validation**: Comprehensive input validation for all operations
- ✅ **Performance**: Connection pooling and request queuing

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/dbankscard/skuvault-mcp-server.git
cd skuvault-mcp-server
```

2. Install dependencies:
```bash
pip install -e .
```

3. Set up authentication:
```bash
cp .env.example .env
# Edit .env and add your SkuVault credentials
```

## 🔧 Configuration

### For Claude Desktop

Add to your Claude Desktop config file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "skuvault": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/skuvault-mcp-server",
      "env": {
        "SKUVAULT_TENANT_TOKEN": "your_tenant_token",
        "SKUVAULT_USER_TOKEN": "your_user_token"
      }
    }
  }
}
```

### Troubleshooting: PYTHONPATH Configuration

If you encounter import errors when running the server, you may need to set the `PYTHONPATH` environment variable. This is necessary because:

1. **Module Structure**: The server uses absolute imports (e.g., `from src.auth import SkuVaultAuth`) which require Python to know where to find the `src` module.
2. **MCP Integration**: When Claude Desktop launches the server, it may not automatically include the project root in Python's module search path.

To fix this, add `PYTHONPATH` to your configuration:

```json
{
  "mcpServers": {
    "skuvault": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/skuvault-mcp-server",
      "env": {
        "PYTHONPATH": "/path/to/skuvault-mcp-server",
        "SKUVAULT_TENANT_TOKEN": "your_tenant_token",
        "SKUVAULT_USER_TOKEN": "your_user_token"
      }
    }
  }
}
```

**Note**: The `PYTHONPATH` should point to the root directory of the project (where the `src` folder is located), not to the `src` folder itself.

## 🛠️ Available Tools

### Product Operations
- `get_product(sku)` - Get product details
- `get_products(page_number, page_size, skus, get_all, active_only)` - List products
- `create_product(...)` - Create new product
- `update_product(...)` - Update product
- `batch_update_products(updates)` - Update multiple products efficiently

### Inventory Management
- `get_inventory_by_location(...)` - Get inventory with filtering
- `add_inventory(...)` - Add inventory
- `remove_inventory(...)` - Remove inventory
- `set_item_quantity(...)` - Set exact quantity

### Analytics
- `get_all_active_products()` - All active products with pagination
- `get_all_inactive_products()` - All inactive products
- `get_low_stock_products(threshold)` - Products at/below reorder point
- `get_product_summary_report()` - Comprehensive statistics

### System Tools
- `get_cache_stats()` - Cache performance metrics
- `clear_cache(pattern)` - Clear cached data
- `get_rate_limits()` - View current rate limits
- `call_api_endpoint(endpoint, **params)` - Access any SkuVault API endpoint

## 📚 Documentation

- **[Best Practices Guide](BEST_PRACTICES.md)** - Detailed workflows and usage patterns
- **[API Schema](api_schema_complete.json)** - Complete API specification

## 💡 Example Questions You Can Ask

### 📦 Product Management
- "Show me details for SKU ABC123"
- "Get all active products"
- "Find all inactive products" 
- "List products with SKUs ABC123, DEF456, and GHI789"
- "Show me all products from brand XYZ"
- "Create a new product with SKU NEW001, description 'Test Product', cost $10"
- "Update the price of SKU ABC123 to $29.99"
- "Update the cost to $15 for SKUs ABC123, DEF456, and GHI789"
- "Change the description of SKU XYZ789 to 'Updated Product Name'"

### 📊 Inventory Analysis
- "What's my current inventory for SKU ABC123?"
- "Show inventory by location for warehouse 1"
- "Get inventory for location A1 in warehouse 2"
- "Show me all products that are low on stock"
- "Which products are at or below their reorder point?"
- "Show me inventory summary for all warehouses"
- "What products have zero quantity?"
- "List all inventory in warehouse 1, location B2"

### 📈 Analytics & Reports  
- "Give me a product summary report"
- "Show product breakdown by brand"
- "How many active vs inactive products do I have?"
- "Show me inventory value by warehouse"
- "Which locations have the most inventory?"
- "Get product statistics including total value"
- "Show me products that need reordering"

### ➕ Add Inventory
- "Add 50 units of SKU ABC123 to warehouse 1, location A1"
- "Receive 100 units of SKU XYZ789 into warehouse 2"
- "Add inventory for SKU DEF456 with a note about the shipment"

### ➖ Remove Inventory
- "Remove 10 units of SKU ABC123 from warehouse 1, location A1"
- "Remove 5 units of SKU XYZ789 for order fulfillment"
- "Deduct inventory for damaged items"

### 🔧 Set Exact Quantities
- "Set the quantity of SKU ABC123 to exactly 100 units in warehouse 1"
- "Update SKU XYZ789 to have 0 units in location B2"
- "Correct the inventory count for SKU DEF456 to 75 units"

### 🏭 Warehouse Operations
- "List all warehouses"
- "Show me warehouse details"
- "Which warehouses do we have?"

### 🔍 Advanced Queries
- "Get the first 10 products"
- "Show me products on page 3 with 50 items per page"
- "Find all products and get complete details"
- "Check inventory across all locations for SKU ABC123"

### 💻 System Operations
- "Show cache statistics"
- "Clear the product cache"
- "Show current rate limits"
- "Clear all cached data"
- "Show queue statistics"

### 🌐 Generic API Access
- "Call the getSuppliers endpoint"
- "Use the getBrands API endpoint"
- "Call getSales endpoint with date range parameters"

## 📝 Natural Language Understanding

The MCP server understands natural variations of these questions:
- "What's in stock for ABC123?" → Gets inventory
- "I need to update prices for multiple products" → Batch update
- "Show me what needs to be reordered" → Low stock report
- "Fix the quantity for this SKU" → Set item quantity

## 🔒 Safety Features

All operations that modify data require explicit confirmation:
- Clear summary of what will be changed
- Visual warnings for destructive operations
- Explicit "yes" or "confirm" required to proceed

To bypass for automation, set `confirm=True` parameter.

## 🏗️ Architecture

```
skuvault-mcp-server/
├── src/
│   ├── server.py          # Main MCP server
│   ├── api_client.py      # SkuVault API client
│   ├── models/            # Pydantic models
│   ├── tools/             # Analytics tools
│   └── utils/             # Utilities (cache, rate limiter, validators)
├── api_schema_complete.json  # Complete API specification
├── pyproject.toml         # Package configuration
└── README.md              # This file
```

## 🧪 Testing

Run the test suite:
```bash
python test_server.py
```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔗 Resources

- [SkuVault API Documentation](https://dev.skuvault.com/reference/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/download)

## ⚡ Quick Start

1. Clone → 2. Install → 3. Configure → 4. Add to Claude Desktop → 5. Start using!

```bash
# Clone and install
git clone https://github.com/dbankscard/skuvault-mcp-server.git
cd skuvault-mcp-server
pip install -e .

# Configure
cp .env.example .env
# Add your tokens to .env

# Test
python test_server.py

# Add to Claude Desktop and start using!
```