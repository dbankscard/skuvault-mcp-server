"""
Analytics and reporting tools for SkuVault data.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


async def get_product_summary(api_client, get_all: bool = True) -> Dict[str, Any]:
    """
    Get a summary of all products with key statistics.
    
    Returns:
        Summary statistics about products including counts by status, brand, etc.
    """
    # Get products - handle pagination properly
    if get_all:
        all_products = []
        page = 0
        
        while True:
            response = await api_client.call_endpoint(
                "getproducts",
                PageNumber=page,
                PageSize=100  # Smaller page size to avoid rate limits
            )
            
            if "error" in response:
                return response
            
            products = response.get("Products", [])
            if not products:
                break
                
            all_products.extend(products)
            
            # Check if we got all products
            total_records = response.get("TotalRecords", 0)
            if len(all_products) >= total_records:
                break
                
            page += 1
            
            # Add small delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.5)
        
        products = all_products
    else:
        # Just get first page
        response = await api_client.call_endpoint(
            "getproducts",
            PageNumber=0,
            PageSize=100
        )
        
        if "error" in response:
            return response
        
        products = response.get("Products", [])
    
    # Calculate statistics
    active_count = sum(1 for p in products if p.get("IsActive", True))
    inactive_count = len(products) - active_count
    
    # Group by brand
    brands = {}
    for product in products:
        brand = product.get("Brand", "No Brand")
        if brand not in brands:
            brands[brand] = 0
        brands[brand] += 1
    
    # Find low stock items (under reorder point)
    low_stock = []
    for product in products:
        reorder_point = product.get("ReorderPoint", 0)
        qty_available = product.get("QuantityAvailable", 0)
        
        if reorder_point > 0 and qty_available < reorder_point:
            low_stock.append({
                "Sku": product.get("Sku"),
                "Description": product.get("Description"),
                "QuantityAvailable": qty_available,
                "ReorderPoint": reorder_point,
                "Shortage": reorder_point - qty_available
            })
    
    # Sort low stock by shortage amount
    low_stock.sort(key=lambda x: x["Shortage"], reverse=True)
    
    return {
        "summary": {
            "total_products": len(products),
            "active_products": active_count,
            "inactive_products": inactive_count,
            "unique_brands": len(brands),
            "low_stock_count": len(low_stock)
        },
        "brands": brands,
        "low_stock_items": low_stock[:20]  # Top 20 low stock items
    }


async def get_inventory_summary(api_client, warehouse_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get a summary of inventory across all locations.
    
    Args:
        warehouse_id: Optional filter by specific warehouse
        
    Returns:
        Summary of inventory by location and warehouse
    """
    # Use proper parameters for the API call
    params = {
        "PageNumber": 0,
        "PageSize": 1000
    }
    
    response = await api_client.call_endpoint("getinventorybylocation", **params)
    
    if "error" in response:
        return response
    
    # Handle both possible response formats
    if isinstance(response, dict) and "Items" in response:
        items = response["Items"]
    elif isinstance(response, list):
        items = response
    else:
        items = []
    
    # Calculate warehouse totals
    warehouse_totals = {}
    location_counts = {}
    total_quantity = 0
    
    for item in items:
        # Handle case where item might be a string or not a dict
        if not isinstance(item, dict):
            continue
            
        wh_id = item.get("WarehouseId")
        location = item.get("LocationCode", "Unknown")
        quantity = item.get("Quantity", 0)
        
        # Warehouse totals
        if wh_id not in warehouse_totals:
            warehouse_totals[wh_id] = {
                "quantity": 0,
                "unique_skus": set(),
                "locations": set()
            }
        
        warehouse_totals[wh_id]["quantity"] += quantity
        warehouse_totals[wh_id]["unique_skus"].add(item.get("Sku"))
        warehouse_totals[wh_id]["locations"].add(location)
        
        # Location counts
        if location not in location_counts:
            location_counts[location] = 0
        location_counts[location] += 1
        
        total_quantity += quantity
    
    # Convert sets to counts
    for wh_id in warehouse_totals:
        warehouse_totals[wh_id]["unique_skus"] = len(warehouse_totals[wh_id]["unique_skus"])
        warehouse_totals[wh_id]["locations"] = len(warehouse_totals[wh_id]["locations"])
    
    return {
        "summary": {
            "total_quantity": total_quantity,
            "unique_items": len(items),
            "warehouse_count": len(warehouse_totals),
            "location_count": len(location_counts)
        },
        "warehouse_totals": warehouse_totals,
        "top_locations": dict(sorted(
            location_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
    }