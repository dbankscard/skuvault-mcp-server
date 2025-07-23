#!/usr/bin/env python3
"""
SkuVault MCP Server - Main server implementation using FastMCP.
"""

import os
import time
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .api_client import SkuVaultClient, SkuVaultAPIError
from .models.skuvault import (
    GetProductRequest,
    GetProductsRequest,
    CreateProductRequest,
    UpdateProductRequest,
    GetWarehousesRequest,
    GetInventoryByLocationRequest,
    SetItemQuantityRequest,
    AddItemRequest,
    RemoveItemRequest
)
from .tools.analytics import get_product_summary, get_inventory_summary
from .utils.cache import global_cache
from .utils.request_queue import global_request_queue
from .utils.rate_limiter import global_rate_limiter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("skuvault")

# Global client instance
client: Optional[SkuVaultClient] = None

# Confirmation requirement flag
REQUIRE_CONFIRMATION = True


def format_confirmation_message(action: str, details: Dict[str, Any]) -> str:
    """Format a confirmation message for the user."""
    lines = [
        f"⚠️  CONFIRMATION REQUIRED: {action}",
        "━" * 50,
    ]
    
    for key, value in details.items():
        lines.append(f"{key}: {value}")
    
    lines.extend([
        "━" * 50,
        "To proceed with this action, please confirm by saying 'yes' or 'confirm'.",
        "To cancel, say 'no' or 'cancel'."
    ])
    
    return "\n".join(lines)


def get_client() -> SkuVaultClient:
    """Get or create the SkuVault client instance."""
    global client
    if client is None:
        tenant_token = os.getenv("SKUVAULT_TENANT_TOKEN")
        user_token = os.getenv("SKUVAULT_USER_TOKEN")
        
        if tenant_token and user_token:
            client = SkuVaultClient(tenant_token, user_token)
        else:
            client = SkuVaultClient()
    
    return client


@mcp.tool()
async def authenticate(email: str, password: str) -> str:
    """
    Authenticate with SkuVault and obtain access tokens.
    
    Args:
        email: SkuVault account email
        password: SkuVault account password
        
    Returns:
        Success message with token status
    """
    try:
        api_client = get_client()
        tokens = await api_client.authenticate(email, password)
        
        # Optionally save tokens to environment for future use
        os.environ["SKUVAULT_TENANT_TOKEN"] = tokens.TenantToken
        os.environ["SKUVAULT_USER_TOKEN"] = tokens.UserToken
        
        return f"Authentication successful. Tokens obtained and stored for session."
    except SkuVaultAPIError as e:
        return f"Authentication failed: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        return f"Authentication error: {str(e)}"


@mcp.tool()
async def get_product(sku: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific product by SKU.
    
    Args:
        sku: The SKU of the product to retrieve
        
    Returns:
        Product details including quantities, pricing, and attributes
    """
    try:
        api_client = get_client()
        
        # Create request
        request = GetProductRequest(
            TenantToken="",  # Will be filled by client
            UserToken="",    # Will be filled by client
            ProductSKU=sku
        )
        
        # Make API call
        response = await api_client.call_endpoint("getproduct", ProductSKU=sku)
        
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error getting product {sku}: {e}")
        return {"error": f"Failed to get product: {str(e)}"}


@mcp.tool()
async def get_products(
    page_number: Optional[int] = None,
    page_size: int = 100,
    skus: Optional[List[str]] = None,
    get_all: bool = False,
    active_only: bool = True,
    include_details: bool = False
) -> Dict[str, Any]:
    """
    Get products with intelligent pagination and filtering.
    
    Args:
        page_number: Specific page number (0-based). If None and get_all=False, returns first page
        page_size: Number of items per page (max 10000)
        skus: Optional list of specific SKUs to retrieve
        get_all: If True, automatically fetches all pages
        active_only: If True, filters to only active products
        include_details: If True, includes full product details (slower for large datasets)
        
    Returns:
        Products with pagination info, or all products if get_all=True
    """
    try:
        api_client = get_client()
        
        # If getting all products, use intelligent pagination
        if get_all:
            all_products = []
            current_page = 0
            total_pages = 1  # Will be updated after first request
            
            logger.info("Fetching all products...")
            
            while current_page < total_pages:
                params = {
                    "PageNumber": current_page,
                    "PageSize": min(page_size, 1000)  # Use reasonable page size for get_all
                }
                
                if skus:
                    params["ProductSKUs"] = skus
                
                response = await api_client.call_endpoint("getproducts", **params)
                
                # Extract products and pagination info
                if "Products" in response:
                    products = response["Products"]
                    
                    # Filter active products if requested
                    if active_only:
                        products = [p for p in products if p.get("IsActive", True)]
                    
                    all_products.extend(products)
                    
                    # Update total pages on first request
                    if current_page == 0:
                        total_records = response.get("TotalRecords", 0)
                        total_pages = (total_records + params["PageSize"] - 1) // params["PageSize"]
                        logger.info(f"Total products: {total_records}, Pages: {total_pages}")
                
                current_page += 1
                
                # Progress indicator for large datasets
                if current_page % 10 == 0:
                    logger.info(f"Progress: {current_page}/{total_pages} pages fetched...")
            
            return {
                "Products": all_products,
                "TotalRecords": len(all_products),
                "Summary": {
                    "total_products": len(all_products),
                    "active_filter": active_only,
                    "pages_fetched": current_page
                }
            }
        
        # Single page request
        else:
            params = {
                "PageNumber": page_number or 0,
                "PageSize": min(page_size, 10000)
            }
            
            if skus:
                params["ProductSKUs"] = skus
            
            response = await api_client.call_endpoint("getproducts", **params)
            
            # Apply active filter if requested
            if active_only and "Products" in response:
                active_products = [p for p in response["Products"] if p.get("IsActive", True)]
                response["Products"] = active_products
                response["FilteredCount"] = len(active_products)
            
            return response
            
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        return {"error": f"Failed to get products: {str(e)}"}


@mcp.tool()
async def create_product(
    sku: str,
    description: str,
    cost: Optional[float] = None,
    sale_price: Optional[float] = None,
    retail_price: Optional[float] = None,
    brand: Optional[str] = None,
    supplier: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Create a new product in SkuVault. REQUIRES CONFIRMATION.
    
    Args:
        sku: Unique SKU for the product
        description: Product description
        cost: Product cost
        sale_price: Sale price
        retail_price: Retail price
        brand: Brand name
        supplier: Supplier name
        confirm: Set to True to confirm the action
        
    Returns:
        Confirmation request or API response with creation status
    """
    # Build details for confirmation
    details = {
        "Action": "Create New Product",
        "SKU": sku,
        "Description": description
    }
    
    if cost is not None:
        details["Cost"] = f"${cost:.2f}"
    if sale_price is not None:
        details["Sale Price"] = f"${sale_price:.2f}"
    if retail_price is not None:
        details["Retail Price"] = f"${retail_price:.2f}"
    if brand:
        details["Brand"] = brand
    if supplier:
        details["Supplier"] = supplier
    
    # Check if confirmation is required
    if REQUIRE_CONFIRMATION and not confirm:
        return {
            "confirmation_required": True,
            "message": format_confirmation_message("Create Product", details),
            "action": "create_product",
            "parameters": {
                "sku": sku,
                "description": description,
                "cost": cost,
                "sale_price": sale_price,
                "retail_price": retail_price,
                "brand": brand,
                "supplier": supplier,
                "confirm": True
            }
        }
    
    # Proceed with the action
    try:
        api_client = get_client()
        
        params = {
            "Sku": sku,
            "Description": description
        }
        
        # Add optional parameters
        if cost is not None:
            params["Cost"] = cost
        if sale_price is not None:
            params["SalePrice"] = sale_price
        if retail_price is not None:
            params["RetailPrice"] = retail_price
        if brand:
            params["Brand"] = brand
        if supplier:
            params["Supplier"] = supplier
        
        response = await api_client.call_endpoint("createproduct", **params)
        
        # Invalidate product-related cache on success
        if not (isinstance(response, dict) and "error" in response):
            global_cache.invalidate("product")
            logger.info(f"Invalidated product cache after creating {sku}")
        
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error creating product {sku}: {e}")
        return {"error": f"Failed to create product: {str(e)}"}


@mcp.tool()
async def update_product(
    sku: str,
    description: Optional[str] = None,
    cost: Optional[float] = None,
    sale_price: Optional[float] = None,
    retail_price: Optional[float] = None,
    brand: Optional[str] = None,
    supplier: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Update an existing product in SkuVault. REQUIRES CONFIRMATION.
    
    Args:
        sku: SKU of the product to update
        description: New product description
        cost: New product cost
        sale_price: New sale price
        retail_price: New retail price
        brand: New brand name
        supplier: New supplier name
        confirm: Set to True to confirm the action
        
    Returns:
        Confirmation request or API response with update status
    """
    # Build details for confirmation
    details = {
        "Action": "Update Product",
        "SKU": sku,
        "Updates": {}
    }
    
    if description is not None:
        details["Updates"]["Description"] = description
    if cost is not None:
        details["Updates"]["Cost"] = f"${cost:.2f}"
    if sale_price is not None:
        details["Updates"]["Sale Price"] = f"${sale_price:.2f}"
    if retail_price is not None:
        details["Updates"]["Retail Price"] = f"${retail_price:.2f}"
    if brand is not None:
        details["Updates"]["Brand"] = brand
    if supplier is not None:
        details["Updates"]["Supplier"] = supplier
    
    # Check if confirmation is required
    if REQUIRE_CONFIRMATION and not confirm:
        return {
            "confirmation_required": True,
            "message": format_confirmation_message("Update Product", details),
            "action": "update_product",
            "parameters": {
                "sku": sku,
                "description": description,
                "cost": cost,
                "sale_price": sale_price,
                "retail_price": retail_price,
                "brand": brand,
                "supplier": supplier,
                "confirm": True
            }
        }
    
    # Proceed with the action
    try:
        api_client = get_client()
        
        params = {"Sku": sku}
        
        # Add parameters to update
        if description is not None:
            params["Description"] = description
        if cost is not None:
            params["Cost"] = cost
        if sale_price is not None:
            params["SalePrice"] = sale_price
        if retail_price is not None:
            params["RetailPrice"] = retail_price
        if brand is not None:
            params["Brand"] = brand
        if supplier is not None:
            params["Supplier"] = supplier
        
        response = await api_client.call_endpoint("updateproduct", **params)
        
        # Invalidate product cache on success
        if not (isinstance(response, dict) and "error" in response):
            global_cache.invalidate("product")
            logger.info(f"Invalidated product cache after updating {sku}")
        
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error updating product {sku}: {e}")
        return {"error": f"Failed to update product: {str(e)}"}


@mcp.tool()
async def get_warehouses() -> Dict[str, Any]:
    """
    Get a list of all warehouses in the SkuVault account.
    
    Returns:
        List of warehouses with IDs, codes, and names
    """
    try:
        api_client = get_client()
        response = await api_client.call_endpoint("getwarehouses")
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error getting warehouses: {e}")
        return {"error": f"Failed to get warehouses: {str(e)}"}


@mcp.tool()
async def get_inventory_by_location(
    page_number: Optional[int] = None,
    page_size: int = 1000,
    skus: Optional[List[str]] = None,
    get_all: bool = False,
    warehouse_id: Optional[int] = None,
    location_code: Optional[str] = None,
    only_with_quantity: bool = False
) -> Dict[str, Any]:
    """
    Get inventory quantities by location with intelligent pagination.
    
    Args:
        page_number: Specific page number (0-based). If None and get_all=False, returns first page
        page_size: Number of items per page (max 10000)
        skus: Optional list of specific SKUs to retrieve
        get_all: If True, automatically fetches all pages
        warehouse_id: Filter by specific warehouse ID
        location_code: Filter by specific location code
        only_with_quantity: If True, only returns items with quantity > 0
        
    Returns:
        Inventory items with location and quantity information
    """
    try:
        api_client = get_client()
        
        # If getting all inventory, use intelligent pagination
        if get_all:
            all_inventory = []
            current_page = 0
            total_pages = 1
            
            logger.info("Fetching all inventory by location...")
            
            while current_page < total_pages:
                params = {
                    "PageNumber": current_page,
                    "PageSize": min(page_size, 1000)
                }
                
                if skus:
                    params["ProductSKUs"] = skus
                
                response = await api_client.call_endpoint("getinventorybylocation", **params)
                
                if "Items" in response:
                    items = response["Items"]
                    
                    # Apply filters
                    if warehouse_id:
                        items = [i for i in items if i.get("WarehouseId") == warehouse_id]
                    
                    if location_code:
                        items = [i for i in items if i.get("LocationCode") == location_code]
                    
                    if only_with_quantity:
                        items = [i for i in items if i.get("Quantity", 0) > 0]
                    
                    all_inventory.extend(items)
                    
                    # Update total pages on first request
                    if current_page == 0:
                        total_records = response.get("TotalRecords", 0)
                        total_pages = (total_records + params["PageSize"] - 1) // params["PageSize"]
                        logger.info(f"Total inventory records: {total_records}, Pages: {total_pages}")
                
                current_page += 1
                
                if current_page % 10 == 0:
                    logger.info(f"Progress: {current_page}/{total_pages} pages fetched...")
            
            # Summarize by location
            location_summary = {}
            for item in all_inventory:
                loc = item.get("LocationCode", "Unknown")
                if loc not in location_summary:
                    location_summary[loc] = {"items": 0, "total_quantity": 0}
                location_summary[loc]["items"] += 1
                location_summary[loc]["total_quantity"] += item.get("Quantity", 0)
            
            return {
                "Items": all_inventory,
                "TotalRecords": len(all_inventory),
                "Summary": {
                    "total_items": len(all_inventory),
                    "unique_locations": len(location_summary),
                    "location_summary": location_summary,
                    "filters_applied": {
                        "warehouse_id": warehouse_id,
                        "location_code": location_code,
                        "only_with_quantity": only_with_quantity
                    }
                }
            }
        
        # Single page request
        else:
            params = {
                "PageNumber": page_number or 0,
                "PageSize": min(page_size, 10000)
            }
            
            if skus:
                params["ProductSKUs"] = skus
            
            response = await api_client.call_endpoint("getinventorybylocation", **params)
            
            # Apply filters to single page if requested
            if any([warehouse_id, location_code, only_with_quantity]) and "Items" in response:
                filtered_items = response["Items"]
                
                if warehouse_id:
                    filtered_items = [i for i in filtered_items if i.get("WarehouseId") == warehouse_id]
                
                if location_code:
                    filtered_items = [i for i in filtered_items if i.get("LocationCode") == location_code]
                
                if only_with_quantity:
                    filtered_items = [i for i in filtered_items if i.get("Quantity", 0) > 0]
                
                response["Items"] = filtered_items
                response["FilteredCount"] = len(filtered_items)
            
            return response
            
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error getting inventory by location: {e}")
        return {"error": f"Failed to get inventory: {str(e)}"}


@mcp.tool()
async def set_item_quantity(
    sku: str,
    warehouse_id: int,
    location_code: str,
    quantity: int,
    update_type: str = "Absolute",
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Set the quantity of an item at a specific location. REQUIRES CONFIRMATION.
    
    Args:
        sku: Product SKU
        warehouse_id: Warehouse ID
        location_code: Location code within the warehouse
        quantity: New quantity value
        update_type: "Absolute" (set to value) or "Relative" (add/subtract)
        confirm: Set to True to confirm the action
        
    Returns:
        Confirmation request or API response with update status
    """
    # Build details for confirmation
    details = {
        "Action": "Set Item Quantity",
        "SKU": sku,
        "Warehouse ID": warehouse_id,
        "Location": location_code,
        "Quantity": quantity,
        "Update Type": update_type
    }
    
    if update_type == "Relative":
        details["Note"] = f"Will {'add' if quantity > 0 else 'subtract'} {abs(quantity)} units"
    else:
        details["Note"] = f"Will set quantity to exactly {quantity} units"
    
    # Check if confirmation is required
    if REQUIRE_CONFIRMATION and not confirm:
        return {
            "confirmation_required": True,
            "message": format_confirmation_message("Set Item Quantity", details),
            "action": "set_item_quantity",
            "parameters": {
                "sku": sku,
                "warehouse_id": warehouse_id,
                "location_code": location_code,
                "quantity": quantity,
                "update_type": update_type,
                "confirm": True
            }
        }
    
    # Proceed with the action
    try:
        api_client = get_client()
        
        params = {
            "Sku": sku,
            "WarehouseId": warehouse_id,
            "LocationCode": location_code,
            "Quantity": quantity,
            "UpdateType": update_type
        }
        
        response = await api_client.call_endpoint("setitemquantity", **params)
        
        # Invalidate inventory cache on success
        if not (isinstance(response, dict) and "error" in response):
            global_cache.invalidate("inventory")
            logger.info(f"Invalidated inventory cache after setting quantity for {sku}")
        
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error setting item quantity: {e}")
        return {"error": f"Failed to set quantity: {str(e)}"}


@mcp.tool()
async def add_inventory(
    sku: str,
    warehouse_id: int,
    location_code: str,
    quantity: int,
    note: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Add inventory to a specific location (receive inventory). REQUIRES CONFIRMATION.
    
    Args:
        sku: Product SKU
        warehouse_id: Warehouse ID
        location_code: Location code within the warehouse
        quantity: Quantity to add
        note: Optional note for the transaction
        confirm: Set to True to confirm the action
        
    Returns:
        Confirmation request or API response with transaction status
    """
    # Build details for confirmation
    details = {
        "Action": "Add Inventory",
        "SKU": sku,
        "Warehouse ID": warehouse_id,
        "Location": location_code,
        "Quantity to Add": f"+{quantity} units"
    }
    
    if note:
        details["Note"] = note
    
    # Check if confirmation is required
    if REQUIRE_CONFIRMATION and not confirm:
        return {
            "confirmation_required": True,
            "message": format_confirmation_message("Add Inventory", details),
            "action": "add_inventory",
            "parameters": {
                "sku": sku,
                "warehouse_id": warehouse_id,
                "location_code": location_code,
                "quantity": quantity,
                "note": note,
                "confirm": True
            }
        }
    
    # Proceed with the action
    try:
        api_client = get_client()
        
        params = {
            "Sku": sku,
            "WarehouseId": warehouse_id,
            "LocationCode": location_code,
            "Quantity": quantity,
            "Reason": "Add"
        }
        
        if note:
            params["Note"] = note
        
        response = await api_client.call_endpoint("additem", **params)
        
        # Invalidate inventory cache on success
        if not (isinstance(response, dict) and "error" in response):
            global_cache.invalidate("inventory")
            logger.info(f"Invalidated inventory cache after adding inventory for {sku}")
        
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error adding inventory: {e}")
        return {"error": f"Failed to add inventory: {str(e)}"}


@mcp.tool()
async def remove_inventory(
    sku: str,
    warehouse_id: int,
    location_code: str,
    quantity: int,
    reason: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Remove inventory from a specific location. REQUIRES CONFIRMATION.
    
    Args:
        sku: Product SKU
        warehouse_id: Warehouse ID
        location_code: Location code within the warehouse
        quantity: Quantity to remove
        reason: Optional reason for removal
        confirm: Set to True to confirm the action
        
    Returns:
        Confirmation request or API response with transaction status
    """
    # Build details for confirmation
    details = {
        "Action": "Remove Inventory",
        "SKU": sku,
        "Warehouse ID": warehouse_id,
        "Location": location_code,
        "Quantity to Remove": f"-{quantity} units",
        "WARNING": "This will permanently reduce inventory!"
    }
    
    if reason:
        details["Reason"] = reason
    
    # Check if confirmation is required
    if REQUIRE_CONFIRMATION and not confirm:
        return {
            "confirmation_required": True,
            "message": format_confirmation_message("Remove Inventory", details),
            "action": "remove_inventory",
            "parameters": {
                "sku": sku,
                "warehouse_id": warehouse_id,
                "location_code": location_code,
                "quantity": quantity,
                "reason": reason,
                "confirm": True
            }
        }
    
    # Proceed with the action
    try:
        api_client = get_client()
        
        params = {
            "Sku": sku,
            "WarehouseId": warehouse_id,
            "LocationCode": location_code,
            "Quantity": quantity,
            "Reason": reason or "Remove"
        }
        
        response = await api_client.call_endpoint("removeitem", **params)
        
        # Invalidate inventory cache on success
        if not (isinstance(response, dict) and "error" in response):
            global_cache.invalidate("inventory")
            logger.info(f"Invalidated inventory cache after removing inventory for {sku}")
        
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error removing inventory: {e}")
        return {"error": f"Failed to remove inventory: {str(e)}"}


@mcp.tool()
async def call_api_endpoint(endpoint_name: str, confirm: bool = False, **parameters) -> Dict[str, Any]:
    """
    Call any SkuVault API endpoint directly. Mutating operations require confirmation.
    
    Args:
        endpoint_name: Name of the endpoint (e.g., "getproduct", "updateproduct")
        confirm: Set to True to confirm mutating actions
        **parameters: Parameters to pass to the endpoint
        
    Returns:
        Confirmation request (for mutating operations) or raw API response
    """
    # List of mutating endpoints that require confirmation
    MUTATING_ENDPOINTS = [
        "additem", "additembulk", "removeitem", "removeitembulk",
        "createproduct", "createproducts", "updateproduct", "updateproducts",
        "setitemquantity", "setitemquantities", "pickitem", "pickitembulk",
        "createkit", "createbrands", "createsuppliers", "createpo",
        "updatepos", "updateshipments", "updatehandlingtime",
        "updateonlinesalestatus", "updatealtskuscodes",
        "syncshippedsaleandremoveitems", "syncshippedsaleandremoveitemsbulk",
        "synconlinesale", "synconlinesales", "addshipments",
        "createholds", "releaseheldquantities", "receivepoitems", "createlot"
    ]
    
    # Check if this is a mutating endpoint
    is_mutating = endpoint_name.lower() in MUTATING_ENDPOINTS
    
    # If mutating and confirmation required
    if is_mutating and REQUIRE_CONFIRMATION and not confirm:
        details = {
            "Action": f"Call API Endpoint",
            "Endpoint": endpoint_name,
            "Parameters": parameters,
            "WARNING": "This is a mutating operation that will modify data!"
        }
        
        return {
            "confirmation_required": True,
            "message": format_confirmation_message(f"API Call: {endpoint_name}", details),
            "action": "call_api_endpoint",
            "parameters": {
                "endpoint_name": endpoint_name,
                "confirm": True,
                **parameters
            }
        }
    
    # Proceed with the API call
    try:
        api_client = get_client()
        response = await api_client.call_endpoint(endpoint_name, **parameters)
        return response
    except SkuVaultAPIError as e:
        return {"error": str(e), "details": e.response_data}
    except Exception as e:
        logger.error(f"Error calling endpoint {endpoint_name}: {e}")
        return {"error": f"Failed to call endpoint: {str(e)}"}


@mcp.tool()
async def get_all_active_products() -> Dict[str, Any]:
    """
    Get all active products with summary statistics.
    This is a convenience method that handles pagination automatically.
    
    Returns:
        All active products with summary information
    """
    return await get_products(get_all=True, active_only=True)


@mcp.tool()
async def get_all_inactive_products() -> Dict[str, Any]:
    """
    Get all inactive products with summary statistics.
    This is a convenience method that handles pagination automatically.
    
    Returns:
        All inactive products with summary information
    """
    # First get all products, then filter for inactive
    response = await get_products(get_all=True, active_only=False)
    
    if "error" in response:
        return response
    
    # Filter for inactive products only
    all_products = response.get("Products", [])
    inactive_products = [p for p in all_products if not p.get("IsActive", True)]
    
    return {
        "Products": inactive_products,
        "TotalRecords": len(inactive_products),
        "Summary": {
            "total_inactive_products": len(inactive_products),
            "status": "inactive",
            "pages_fetched": response.get("Summary", {}).get("pages_fetched", 0)
        }
    }


@mcp.tool()
async def get_products_by_status(
    status: str = "all",
    include_summary: bool = True
) -> Dict[str, Any]:
    """
    Get all products filtered by status with detailed breakdown.
    
    Args:
        status: Filter by status - "active", "inactive", or "all"
        include_summary: Include summary statistics
        
    Returns:
        Products filtered by status with optional summary
    """
    # Get all products
    response = await get_products(get_all=True, active_only=False)
    
    if "error" in response:
        return response
    
    all_products = response.get("Products", [])
    
    # Filter by status
    if status.lower() == "active":
        filtered_products = [p for p in all_products if p.get("IsActive", True)]
    elif status.lower() == "inactive":
        filtered_products = [p for p in all_products if not p.get("IsActive", True)]
    else:  # "all" or any other value
        filtered_products = all_products
    
    result = {
        "Products": filtered_products,
        "TotalRecords": len(filtered_products),
        "Filter": status
    }
    
    # Add summary if requested
    if include_summary:
        active_count = sum(1 for p in all_products if p.get("IsActive", True))
        inactive_count = len(all_products) - active_count
        
        # Group by brand for filtered products
        brands = {}
        for product in filtered_products:
            brand = product.get("Brand", "No Brand")
            if brand not in brands:
                brands[brand] = 0
            brands[brand] += 1
        
        result["Summary"] = {
            "total_products": len(all_products),
            "active_products": active_count,
            "inactive_products": inactive_count,
            "filtered_count": len(filtered_products),
            "brands_in_filter": len(brands),
            "top_brands": dict(sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    return result


@mcp.tool()
async def get_low_stock_products(reorder_threshold_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Get products that are at or below their reorder point.
    
    Args:
        reorder_threshold_multiplier: Multiplier for reorder point (1.0 = at reorder point, 1.5 = 50% above)
        
    Returns:
        Products with low stock, sorted by shortage severity
    """
    try:
        api_client = get_client()
        
        # Get all active products
        response = await get_products(get_all=True, active_only=True)
        
        if "error" in response:
            return response
        
        products = response.get("Products", [])
        
        # Find low stock items
        low_stock = []
        for product in products:
            reorder_point = product.get("ReorderPoint", 0)
            qty_available = product.get("QuantityAvailable", 0)
            
            if reorder_point > 0:
                threshold = reorder_point * reorder_threshold_multiplier
                if qty_available <= threshold:
                    low_stock.append({
                        "Sku": product.get("Sku"),
                        "Description": product.get("Description"),
                        "Brand": product.get("Brand"),
                        "QuantityAvailable": qty_available,
                        "QuantityOnHand": product.get("QuantityOnHand", 0),
                        "QuantityIncoming": product.get("QuantityIncoming", 0),
                        "ReorderPoint": reorder_point,
                        "Shortage": max(0, reorder_point - qty_available),
                        "PercentOfReorderPoint": round((qty_available / reorder_point * 100) if reorder_point > 0 else 0, 1)
                    })
        
        # Sort by shortage severity
        low_stock.sort(key=lambda x: x["Shortage"], reverse=True)
        
        return {
            "low_stock_products": low_stock,
            "summary": {
                "total_low_stock": len(low_stock),
                "critical_stock": len([p for p in low_stock if p["QuantityAvailable"] == 0]),
                "threshold_multiplier": reorder_threshold_multiplier
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting low stock products: {e}")
        return {"error": f"Failed to get low stock products: {str(e)}"}


@mcp.tool()
async def get_product_summary_report() -> Dict[str, Any]:
    """
    Get a comprehensive summary report of all products.
    Includes statistics by brand, status, and stock levels.
    
    Returns:
        Comprehensive product summary with analytics
    """
    try:
        api_client = get_client()
        return await get_product_summary(api_client, get_all=True)
    except Exception as e:
        logger.error(f"Error getting product summary: {e}")
        return {"error": f"Failed to get product summary: {str(e)}"}


@mcp.tool()
async def get_inventory_summary_report(warehouse_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get a comprehensive summary of inventory across locations.
    
    Args:
        warehouse_id: Optional filter by specific warehouse
        
    Returns:
        Inventory summary with location and warehouse analytics
    """
    try:
        api_client = get_client()
        return await get_inventory_summary(api_client, warehouse_id)
    except Exception as e:
        logger.error(f"Error getting inventory summary: {e}")
        return {"error": f"Failed to get inventory summary: {str(e)}"}


@mcp.tool()
async def batch_update_products(
    updates: List[Dict[str, Any]],
    confirm: bool = False
) -> Dict[str, Any]:
    """
    Update multiple products in a single batch operation.
    
    Args:
        updates: List of product updates. Each item should contain:
            - Sku: Product SKU (required)
            - Any other fields to update (Description, Cost, Price, etc.)
        confirm: Set to True to confirm the batch update
        
    Returns:
        Results of the batch update operation
    """
    # Import validators
    from .utils.validators import validate_sku, validate_bulk_items
    
    # Validate bulk items
    is_valid, error_msg = validate_bulk_items(updates, max_items=100)
    if not is_valid:
        return {"error": error_msg}
    
    # Validate each SKU
    for idx, update in enumerate(updates):
        if "Sku" not in update:
            return {"error": f"Item {idx}: Missing required field 'Sku'"}
        
        is_valid, error_msg = validate_sku(update["Sku"])
        if not is_valid:
            return {"error": f"Item {idx} - SKU '{update['Sku']}': {error_msg}"}
    
    # Check if confirmation is required
    if REQUIRE_CONFIRMATION and not confirm:
        details = {
            "Action": "Batch Update Products",
            "Number of Products": len(updates),
            "SKUs to Update": [u["Sku"] for u in updates[:5]] + (["..."] if len(updates) > 5 else []),
            "Sample Changes": updates[0] if updates else {}
        }
        
        return {
            "confirmation_required": True,
            "message": format_confirmation_message("Batch Update Products", details),
            "action": "batch_update_products",
            "parameters": {
                "updates": updates,
                "confirm": True
            }
        }
    
    # Process batch update
    try:
        api_client = get_client()
        results = {
            "successful": 0,
            "failed": 0,
            "results": []
        }
        
        # Use request queue for batch processing
        async def update_product(update_data):
            try:
                response = await api_client.call_endpoint("updateproduct", **update_data)
                if "error" not in response:
                    results["successful"] += 1
                    return {"sku": update_data["Sku"], "status": "success"}
                else:
                    results["failed"] += 1
                    return {"sku": update_data["Sku"], "status": "failed", "error": response["error"]}
            except Exception as e:
                results["failed"] += 1
                return {"sku": update_data["Sku"], "status": "failed", "error": str(e)}
        
        # Process updates in batches to respect rate limits
        batch_size = 5  # Process 5 at a time
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            batch_results = await asyncio.gather(*[update_product(u) for u in batch])
            results["results"].extend(batch_results)
            
            # Small delay between batches
            if i + batch_size < len(updates):
                await asyncio.sleep(1)
        
        # Invalidate product cache after batch update
        if results["successful"] > 0:
            global_cache.invalidate("product")
            logger.info(f"Invalidated product cache after batch update ({results['successful']} products)")
        
        return {
            "summary": {
                "total": len(updates),
                "successful": results["successful"],
                "failed": results["failed"]
            },
            "details": results["results"]
        }
        
    except Exception as e:
        logger.error(f"Error in batch update: {e}")
        return {"error": f"Batch update failed: {str(e)}"}


@mcp.tool()
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics and performance metrics.
    
    Returns:
        Cache statistics including hit rate and memory usage
    """
    return {
        "cache_stats": global_cache.get_stats(),
        "info": "Cache helps reduce API calls and improve response times"
    }


@mcp.tool()
async def clear_cache(pattern: Optional[str] = None) -> Dict[str, Any]:
    """
    Clear cached data to force fresh API calls.
    
    Args:
        pattern: Optional pattern to match (e.g., "product", "inventory")
        
    Returns:
        Number of cache entries cleared
    """
    count = global_cache.invalidate(pattern)
    
    return {
        "cleared": count,
        "pattern": pattern or "all",
        "message": f"Cleared {count} cache entries"
    }


@mcp.tool()
async def get_queue_stats() -> Dict[str, Any]:
    """
    Get request queue statistics for bulk operations.
    
    Returns:
        Queue statistics and status
    """
    stats = global_request_queue.get_queue_stats()
    
    return {
        "queue_stats": stats,
        "info": "Queue helps manage bulk operations without hitting rate limits"
    }


@mcp.tool()
async def check_authentication() -> Dict[str, Any]:
    """
    Check if authentication tokens are loaded and working.
    
    Returns:
        Authentication status and token availability
    """
    tenant_token = os.getenv("SKUVAULT_TENANT_TOKEN")
    user_token = os.getenv("SKUVAULT_USER_TOKEN")
    
    api_client = get_client()
    has_tokens = api_client.auth_tokens is not None
    
    return {
        "tenant_token_configured": bool(tenant_token),
        "user_token_configured": bool(user_token),
        "client_has_tokens": has_tokens,
        "ready_for_api_calls": has_tokens,
        "tenant_token_preview": tenant_token[:10] + "..." if tenant_token else None,
        "user_token_preview": user_token[:10] + "..." if user_token else None
    }


@mcp.tool()
async def test_api_connection() -> Dict[str, Any]:
    """
    Test the API connection by trying to get warehouses.
    
    Returns:
        Connection test results
    """
    try:
        api_client = get_client()
        
        # Check if client has tokens
        if not api_client.auth_tokens:
            return {
                "status": "error",
                "message": "No authentication tokens available",
                "suggestion": "Check that SKUVAULT_TENANT_TOKEN and SKUVAULT_USER_TOKEN are set in environment"
            }
        
        # Try a simple API call
        response = await api_client.call_endpoint("getwarehouses")
        
        if "error" in response:
            return {
                "status": "error", 
                "message": f"API call failed: {response['error']}",
                "has_tokens": True
            }
        else:
            return {
                "status": "success",
                "message": "API connection working",
                "warehouses_found": len(response.get("Warehouses", [])),
                "has_tokens": True
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection test failed: {str(e)}",
            "has_tokens": api_client.auth_tokens is not None if 'api_client' in locals() else False
        }


@mcp.tool()
async def get_rate_limits() -> Dict[str, Any]:
    """
    Get current rate limits for all endpoints.
    
    Returns:
        Current rate limits and backoff status
    """
    current_time = time.time()
    
    # Get rate limits
    limits = {}
    for endpoint, limit in global_rate_limiter.rate_limits.items():
        limits[endpoint] = f"{limit} calls/minute"
    
    # Get current backoff status
    backoffs = {}
    for endpoint, until_time in global_rate_limiter.backoff_until.items():
        remaining = until_time - current_time
        if remaining > 0:
            backoffs[endpoint] = f"{remaining:.1f} seconds"
    
    # Get last call times
    last_calls = {}
    for endpoint, last_time in global_rate_limiter.last_call_times.items():
        time_ago = current_time - last_time
        last_calls[endpoint] = f"{time_ago:.1f} seconds ago"
    
    return {
        "rate_limits": limits,
        "endpoints_in_backoff": backoffs,
        "last_api_calls": last_calls,
        "info": "Rate limits are dynamically updated based on API responses"
    }


def main():
    """Main entry point for the server."""
    import asyncio
    
    async def cleanup():
        """Cleanup function to close the client."""
        global client
        if client:
            await client.close()
    
    try:
        mcp.run()
    finally:
        asyncio.run(cleanup())


# Run the server
if __name__ == "__main__":
    main()