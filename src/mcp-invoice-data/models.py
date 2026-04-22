"""Pydantic models for MCP Invoice Data.

Defines data structures for invoices and purchase orders.
Based on INVOICE_EXTRACTION_SCHEMA for document intelligence integration.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item on an invoice or purchase order."""

    description: str
    quantity: float
    unit_price: float
    uom: Optional[str] = None  # Unit of measure
    total: float


class Supplier(BaseModel):
    """Supplier/vendor information."""

    name: str
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class BillTo(BaseModel):
    """Billing destination information."""

    name: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None


class PurchaseOrder(BaseModel):
    """A purchase order record derived from the PURCHASE_ORDERS mock catalog."""

    po_number: str
    due_date: Optional[str] = None
    currency: str = "EUR"
    supplier: Supplier
    bill_to: Optional[BillTo] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    total: float
    confidence: Optional[float] = None
    notes: Optional[str] = None
    status: str = "submitted"
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None

    @property
    def vendor_name(self) -> str:
        """Helper that exposes the supplier name for logging helpers."""
        return self.supplier.name


class Invoice(BaseModel):
    """An invoice record matching INVOICE_EXTRACTION_SCHEMA."""

    po_number: Optional[str] = None
    invoice_number: str
    invoice_date: str  # ISO 8601 date
    due_date: Optional[str] = None  # ISO 8601 date
    currency: str = "EUR"  # Three letter ISO currency code
    supplier: Supplier
    bill_to: Optional[BillTo] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    shipping: Optional[float] = None
    total: float
    confidence: Optional[float] = None  # 0-1 confidence score
    notes: Optional[str] = None
    status: str = "pending"  # pending, approved, paid, rejected


class POCheckResult(BaseModel):
    """Result of a purchase order validation check."""

    po_number: str
    exists: bool
    is_valid: bool
    message: str
