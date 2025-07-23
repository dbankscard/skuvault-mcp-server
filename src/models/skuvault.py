"""
Pydantic models for SkuVault API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AuthTokens(BaseModel):
    """Authentication tokens required for all API requests."""
    TenantToken: str = Field(..., description="Unique identifier for the SkuVault account")
    UserToken: str = Field(..., description="User-specific authentication token")


class BaseRequest(BaseModel):
    """Base request model with authentication tokens."""
    TenantToken: str
    UserToken: str


class GetTokensRequest(BaseModel):
    """Request model for obtaining authentication tokens."""
    Email: str
    Password: str


class GetTokensResponse(BaseModel):
    """Response model for authentication tokens."""
    TenantToken: str
    UserToken: str


class Product(BaseModel):
    """Product model with all available fields."""
    Sku: Optional[str] = None
    Code: Optional[str] = None
    Description: Optional[str] = None
    ShortDescription: Optional[str] = None
    LongDescription: Optional[str] = None
    Cost: Optional[float] = None
    RetailPrice: Optional[float] = None
    SalePrice: Optional[float] = None
    Weight: Optional[float] = None
    WeightUnit: Optional[str] = None
    Brand: Optional[str] = None
    Supplier: Optional[str] = None
    CreatedDateUtc: Optional[datetime] = None
    ModifiedDateUtc: Optional[datetime] = None
    QuantityOnHand: Optional[int] = None
    QuantityAvailable: Optional[int] = None
    QuantityPending: Optional[int] = None
    QuantityIncoming: Optional[int] = None


class GetProductRequest(BaseRequest):
    """Request model for getting a single product."""
    ProductSKU: str = Field(..., description="The SKU of the product to retrieve")


class GetProductsRequest(BaseRequest):
    """Request model for getting multiple products."""
    PageNumber: Optional[int] = Field(0, description="Page number (0-based)")
    PageSize: Optional[int] = Field(100, description="Number of items per page")
    IncludeDeleted: Optional[bool] = Field(False, description="Include deleted products")
    ProductSKUs: Optional[List[str]] = Field(None, description="List of specific SKUs to retrieve")


class CreateProductRequest(BaseRequest):
    """Request model for creating a product."""
    Sku: str
    Description: Optional[str] = None
    ShortDescription: Optional[str] = None
    LongDescription: Optional[str] = None
    Classification: Optional[str] = None
    Supplier: Optional[str] = None
    Brand: Optional[str] = None
    Cost: Optional[float] = None
    SalePrice: Optional[float] = None
    RetailPrice: Optional[float] = None
    VariationParentSku: Optional[str] = None
    IsActive: Optional[bool] = True
    Weight: Optional[float] = None
    WeightUnit: Optional[str] = None
    MinimumOrderQuantity: Optional[int] = None
    MinimumOrderQuantityInfo: Optional[str] = None
    MaximumOrderQuantity: Optional[int] = None
    QuantityPerCase: Optional[int] = None


class UpdateProductRequest(BaseRequest):
    """Request model for updating a product."""
    Sku: str
    Description: Optional[str] = None
    ShortDescription: Optional[str] = None
    LongDescription: Optional[str] = None
    Classification: Optional[str] = None
    Supplier: Optional[str] = None
    Brand: Optional[str] = None
    Cost: Optional[float] = None
    SalePrice: Optional[float] = None
    RetailPrice: Optional[float] = None
    Weight: Optional[float] = None
    WeightUnit: Optional[str] = None
    ReorderPoint: Optional[int] = None
    RestockLevel: Optional[int] = None


class Warehouse(BaseModel):
    """Warehouse model."""
    Id: int
    Code: str
    Name: str
    ContactEmail: Optional[str] = None
    IsEnabled: bool = True


class GetWarehousesRequest(BaseRequest):
    """Request model for getting warehouses."""
    pass


class InventoryItem(BaseModel):
    """Inventory item with quantity and location information."""
    Sku: str
    WarehouseId: int
    LocationCode: Optional[str] = None
    Quantity: int
    QuantityAvailable: Optional[int] = None
    QuantityPending: Optional[int] = None


class SetItemQuantityRequest(BaseRequest):
    """Request model for setting item quantity."""
    Sku: Optional[str] = None
    Code: Optional[str] = None
    LocationCode: str
    Quantity: int
    WarehouseId: int
    UpdateType: Optional[str] = Field("Absolute", description="Absolute or Relative")
    Note: Optional[str] = None


class GetInventoryByLocationRequest(BaseRequest):
    """Request model for getting inventory by location."""
    IsReturnByCodes: Optional[bool] = False
    PageNumber: Optional[int] = 0
    PageSize: Optional[int] = 10000
    ProductSKUs: Optional[List[str]] = None
    ProductCodes: Optional[List[str]] = None


class AddItemRequest(BaseRequest):
    """Request model for adding inventory."""
    Sku: Optional[str] = None
    Code: Optional[str] = None
    WarehouseId: int
    LocationCode: str
    Quantity: int
    IncrementalMode: Optional[bool] = True
    Note: Optional[str] = None


class RemoveItemRequest(BaseRequest):
    """Request model for removing inventory."""
    Sku: Optional[str] = None
    Code: Optional[str] = None
    WarehouseId: int
    LocationCode: str
    Quantity: int
    Reason: Optional[str] = None


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    Status: Optional[str] = None
    Errors: Optional[List[str]] = None
    Data: Optional[Dict[str, Any]] = None


class ProductsResponse(BaseModel):
    """Response model for multiple products."""
    Products: List[Product]
    PageNumber: int
    PageSize: int
    TotalRecords: int


class WarehousesResponse(BaseModel):
    """Response model for warehouses."""
    Warehouses: List[Warehouse]


class InventoryResponse(BaseModel):
    """Response model for inventory queries."""
    Items: List[InventoryItem]
    PageNumber: Optional[int] = None
    PageSize: Optional[int] = None
    TotalRecords: Optional[int] = None