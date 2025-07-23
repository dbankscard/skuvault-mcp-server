# SkuVault MCP Server - Best Practices & Workflows

This guide helps you effectively use the SkuVault MCP server, especially if you're not familiar with your warehouse structure, SKUs, or location codes.

## Table of Contents
1. [Getting Started - Discovery First](#getting-started---discovery-first)
2. [Common Workflows](#common-workflows)
3. [Safety Best Practices](#safety-best-practices)
4. [Troubleshooting Common Issues](#troubleshooting-common-issues)
5. [Pro Tips](#pro-tips)

## Getting Started - Discovery First

Before performing any operations, discover your SkuVault structure:

### 1. Find Your Warehouses
Always start by understanding what warehouses you have:
```
"List all warehouses"
"Show me warehouse details"
```

Example response might show:
- Warehouse ID: 12345, Code: MAIN (Main Warehouse)
- Warehouse ID: 67890, Code: WEST (West Coast Facility)

### 2. Understand Your Products
Before working with products, explore what you have:
```
"Show me the first 10 products"
"Get all active products"
"Search for products with SKU containing WIDGET"
```

### 3. Discover Locations
Locations are required for inventory operations:
```
"Show locations in warehouse 12345"
"What locations exist in the Main warehouse?"
```

## Common Workflows

### Workflow 1: Adding Inventory (When You Don't Know the Details)

**Step 1: Find the product**
```
User: "Show me details for SKU WIDGET-001"
```

**Step 2: Check current inventory**
```
User: "Where is WIDGET-001 currently located?"
or
User: "Show inventory for SKU WIDGET-001"
```

**Step 3: Find available locations**
```
User: "Show me empty locations in warehouse 12345"
or
User: "List locations in warehouse 12345"
```

**Step 4: Add inventory**
```
User: "Add 10 units of WIDGET-001 to location A1-B2 in warehouse 12345"
```

### Workflow 2: Moving Inventory Between Locations

**Step 1: Find current location**
```
User: "Show me inventory locations for SKU GADGET-002"
```

**Step 2: Remove from source**
```
User: "Remove 5 units of GADGET-002 from location A1-B2 in warehouse 12345"
```

**Step 3: Add to destination**
```
User: "Add 5 units of GADGET-002 to location B2-C3 in warehouse 12345"
```

### Workflow 3: Inventory Audit

**Step 1: Get current quantity**
```
User: "What's the current inventory for SKU GIZMO-003?"
```

**Step 2: Set correct quantity**
```
User: "Set the quantity of GIZMO-003 to exactly 100 units in location C3-D4 warehouse 12345"
```

### Workflow 4: Product Management

**Step 1: Search for products**
```
User: "Find all products from brand Acme Corp"
or
User: "Show me inactive products"
```

**Step 2: Update product details**
```
User: "Update the price of SKU WIDGET-001 to $29.99"
```

**Step 3: Batch updates**
```
User: "Update the cost to $15 for SKUs WIDGET-001, GADGET-002, and GIZMO-003"
```

### Workflow 5: Low Stock Management

**Step 1: Find low stock items**
```
User: "Show me products that are low on stock"
or
User: "Which products are at or below their reorder point?"
```

**Step 2: Review specific product**
```
User: "Show me details for SKU DEVICE-004"
```

**Step 3: Add inventory**
```
User: "Add 50 units of DEVICE-004 to location D4-E5 in warehouse 12345"
```

## Safety Best Practices

### 1. Always Verify Before Modifying
- Check current state before making changes
- Use "get" operations before "update" operations
- Confirm warehouse IDs and location codes

### 2. Confirmation Requirements
The server requires confirmation for destructive operations:
- Adding inventory
- Removing inventory
- Updating products
- Setting quantities

When prompted, review the details carefully before confirming.

### 3. Use Descriptive Notes
When adding/removing inventory, include notes:
```
User: "Add 100 units of WIDGET-001 to location A1-B2 in warehouse 12345 with note 'Received from PO#PO-2024-001'"
```

### 4. Batch Operations Safely
For multiple updates:
- Test with one item first
- Review the batch before confirming
- Keep batch sizes reasonable (10-20 items)

## Troubleshooting Common Issues

### Issue: "LocationNotFound"
**Solution**: List locations first
```
User: "Show locations in warehouse 12345"
```
Then use an exact location code like "A1-B2" (not just "A1")

### Issue: "ProductNotFoundInLocation"
**Solution**: Check where the product actually is
```
User: "Show inventory locations for SKU GADGET-002"
```

### Issue: "SKU Not Found"
**Solution**: Verify the exact SKU
```
User: "Search for products containing WIDGET"
```

### Issue: Don't Know Warehouse ID
**Solution**: Use warehouse name/code
```
User: "Show me warehouses"
```
Then use the ID from the response

## Pro Tips

### 1. Create Shortcuts for Common Operations
Instead of remembering IDs, ask naturally:
```
"Show me what's in the Main warehouse"
"Add inventory to the main warehouse"
```

### 2. Use Reports for Overview
Get summaries before diving into details:
```
"Give me a product summary report"
"Show inventory summary for all warehouses"
```

### 3. Cache-Friendly Queries
The server caches responses. Repeated queries are faster:
- Product details
- Warehouse lists
- Location lists

### 4. Natural Language Works
You don't need exact command syntax:
- ❌ "get_product sku=WIDGET-001"
- ✅ "Show me product WIDGET-001"
- ✅ "What's in stock for WIDGET-001?"
- ✅ "I need details about SKU WIDGET-001"

### 5. Chain Operations Logically
Think in workflows:
1. Discover → 2. Verify → 3. Modify → 4. Confirm

### 6. Use Analytics Tools
Get insights without manual counting:
```
"Which locations have the most inventory?"
"Show me products by brand"
"What needs to be reordered?"
```

## Example Full Workflow: Receiving New Inventory

```
User: "I need to receive 50 units of product GIZMO-003"

Server: "Let me help you receive that inventory. First, let me check if product GIZMO-003 exists."
[Server checks product]

User: "Show me warehouses"

Server: [Shows warehouses:]
- Warehouse ID: 12345, Code: MAIN (Main Warehouse)
- Warehouse ID: 67890, Code: WEST (West Coast Facility)

User: "Show me available locations in warehouse 12345"

Server: [Shows locations like A1-B2, B2-C3, C3-D4, etc.]

User: "Check if there's already inventory of GIZMO-003 in any location"

Server: "GIZMO-003 currently has 25 units in location C3-D4"

User: "Add 50 units of GIZMO-003 to location C3-D4 in warehouse 12345"

Server: "⚠️ CONFIRMATION REQUIRED: Add Inventory
SKU: GIZMO-003
Warehouse ID: 12345
Location: C3-D4
Quantity to Add: +50 units
To proceed, please confirm by saying 'yes' or 'confirm'."

User: "Yes"

Server: "Successfully added 50 units. Location C3-D4 now has 75 units of GIZMO-003."
```

## Understanding Required Parameters

### Tools That Need Full Details Upfront

These tools require all parameters when called:

1. **add_inventory**
   - Required: SKU, warehouse_id, location_code, quantity
   - Optional: note

2. **remove_inventory**
   - Required: SKU, warehouse_id, location_code, quantity
   - Optional: reason (defaults to "Remove")

3. **set_item_quantity**
   - Required: SKU, warehouse_id, location_code, quantity

### Tools That Help You Discover Information

Use these to find the required parameters:

1. **get_warehouses** - Find warehouse IDs
2. **get_locations** - Find valid location codes
3. **get_product** - Verify SKUs exist
4. **get_inventory_by_location** - Find where items are stored

## Quick Reference Commands

### Discovery Commands
```
"Show me all warehouses"
"List locations in warehouse 12345"
"Where is SKU WIDGET-001 located?"
"Show me product WIDGET-001"
"What's in location A1-B2 at warehouse 12345?"
```

### Action Commands (Need All Details)
```
"Add 100 units of WIDGET-001 to location A1-B2 in warehouse 12345"
"Remove 50 units of GADGET-002 from location B2-C3 in warehouse 12345"
"Set GIZMO-003 quantity to 100 in location C3-D4 at warehouse 12345"
"Update price of WIDGET-001 to $29.99"
```

### Report Commands
```
"Show product summary report"
"Show inventory summary"
"Which products are low on stock?"
"Show me all active/inactive products"
```

## Best Practice Summary

1. **Always start with discovery** - Don't guess IDs or locations
2. **Verify before modifying** - Check current state first
3. **Use exact codes** - "A1-1" not "A1", exact SKUs not partial
4. **Review confirmations** - Read what will change before confirming
5. **Think in workflows** - Plan your steps before executing
6. **Use notes** - Document why you're making changes
7. **Cache is your friend** - Repeated queries are faster

## Common Patterns

### Pattern: Daily Inventory Receiving
```
1. "Show me today's receiving list" (if integrated)
2. "List warehouses"
3. "Show locations in warehouse 12345"
4. For each item: "Add 50 of WIDGET-001 to A1-B2 in warehouse 12345"
```

### Pattern: Inventory Count Verification
```
1. "Show inventory for location A1-B2"
2. For each discrepancy: "Set WIDGET-001 to 100 in A1-B2"
```

### Pattern: Low Stock Replenishment
```
1. "Show me low stock items"
2. "Where is TOOL-005 currently stored?"
3. "Add 200 of TOOL-005 to E5-F6 in warehouse 67890"
```

Remember: The server is designed to help you work safely with your inventory. When in doubt, explore first, then act!