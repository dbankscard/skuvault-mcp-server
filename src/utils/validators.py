"""
Validation utilities for SkuVault data.
"""

import re
from typing import Optional, List


def validate_sku(sku: str) -> tuple[bool, Optional[str]]:
    """
    Validate SKU format according to SkuVault requirements.
    
    Args:
        sku: The SKU to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not sku:
        return False, "SKU cannot be empty"
    
    if len(sku) > 100:
        return False, "SKU cannot exceed 100 characters"
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', '?', '<', '>', '|', '"', '*']
    for char in invalid_chars:
        if char in sku:
            return False, f"SKU cannot contain character: {char}"
    
    # Check for leading/trailing whitespace
    if sku != sku.strip():
        return False, "SKU cannot have leading or trailing whitespace"
    
    return True, None


def validate_quantity(quantity: int, context: str = "quantity") -> tuple[bool, Optional[str]]:
    """
    Validate quantity values.
    
    Args:
        quantity: The quantity to validate
        context: Context for error message (e.g., "quantity", "reorder point")
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if quantity < 0:
        return False, f"{context.capitalize()} cannot be negative"
    
    if quantity > 999999999:
        return False, f"{context.capitalize()} exceeds maximum allowed value"
    
    return True, None


def validate_warehouse_id(warehouse_id: Optional[int]) -> tuple[bool, Optional[str]]:
    """
    Validate warehouse ID.
    
    Args:
        warehouse_id: The warehouse ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if warehouse_id is None:
        return True, None  # Optional field
    
    if warehouse_id <= 0:
        return False, "Warehouse ID must be positive"
    
    return True, None


def validate_location_code(location_code: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate location code format.
    
    Args:
        location_code: The location code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not location_code:
        return True, None  # Optional field
    
    if len(location_code) > 50:
        return False, "Location code cannot exceed 50 characters"
    
    # Basic alphanumeric check with some common separators
    if not re.match(r'^[A-Za-z0-9\-_.]+$', location_code):
        return False, "Location code contains invalid characters"
    
    return True, None


def validate_price(price: float, context: str = "price") -> tuple[bool, Optional[str]]:
    """
    Validate price values.
    
    Args:
        price: The price to validate
        context: Context for error message (e.g., "price", "cost", "retail price")
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if price < 0:
        return False, f"{context.capitalize()} cannot be negative"
    
    if price > 9999999.99:
        return False, f"{context.capitalize()} exceeds maximum allowed value"
    
    # Check for reasonable decimal places (2 for currency)
    if len(str(price).split('.')[-1]) > 2:
        return False, f"{context.capitalize()} should have at most 2 decimal places"
    
    return True, None


def validate_barcode(barcode: str) -> tuple[bool, Optional[str]]:
    """
    Validate barcode format.
    
    Args:
        barcode: The barcode to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not barcode:
        return True, None  # Optional field
    
    if len(barcode) > 50:
        return False, "Barcode cannot exceed 50 characters"
    
    # Allow alphanumeric and common barcode characters
    if not re.match(r'^[A-Za-z0-9\-]+$', barcode):
        return False, "Barcode contains invalid characters"
    
    return True, None


def validate_bulk_items(items: List[dict], max_items: int = 100) -> tuple[bool, Optional[str]]:
    """
    Validate bulk operation items.
    
    Args:
        items: List of items for bulk operation
        max_items: Maximum allowed items in one operation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not items:
        return False, "No items provided for bulk operation"
    
    if len(items) > max_items:
        return False, f"Bulk operation exceeds maximum of {max_items} items"
    
    return True, None