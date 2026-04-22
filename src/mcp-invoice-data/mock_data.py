"""Mock data generator for Invoice Data.

Provides realistic mock data for invoices and purchase orders.
Uses curated data for demo purposes.
"""

from typing import Optional

from models import (
    Invoice,
    LineItem,
    PurchaseOrder,
    POCheckResult,
    Supplier,
    BillTo,
)


# ============================================================================
# Curated Invoice and Purchase Order Data
# ============================================================================

PURCHASE_ORDERS = {
    "534": {
        "po_number": "534",
        "due_date": "2025-10-15",
        "currency": "EUR",
        "supplier": {
            "name": "Zava Specialty Coffee",
            "address": "333 3rd Ave, Seattle, WA 12345",
            "email": None,
            "phone": "123-456-7890",
        },
        
        "line_items": [
            {"description": "Zava Ethiopia for Espresso", "quantity": 80, "unit_price": 20, "uom": "Kg", "total": 2000},
        ],
        "subtotal": 2000,
        "tax": 300,
        "shipping": 0,
        "total": 2300,
        "status": "approved",
    },
    "888": {
        "po_number": "888",
        "due_date": "2205-10-16",
        "currency": "USD",
        "supplier": {
            "name": "Contoso Fin Consulting",
            "address": "450 East 78th Ave, Denver, CO 12345",
            "email": None,
            "phone": "(123) 456-7890",
        },
        "line_items": [
            {
                "description": "Consultation services implementation of AI powered grinder",
                "quantity": 3,
                "unit_price": 375,
                "uom": "hours",
                "total": 1125,
            },
        ],
        "subtotal": 1125,
        "tax": 0,
        "shipping": 0,
        "total": 1125,
        "status": "pending",
    },
    
    
}

INVOICES = {
    "100" : {
        "po_number": "534",
        "invoice_number": "100",
        "invoice_date": "2025-10-15",
        "due_date": "",
        "currency": "EUR",
        "supplier": {
            "name": "Zava Specialty Coffee",
            "address": "333 3rd Ave, Seattle, WA 12345",
            "email": "",
            "phone": "123-456-7890"
        },
        "bill_to": {
            "name": "Tomas Kubica",
            "address": "Karlinska 1918, Karlin, Czechia",
            "department": "CoPilot Inc"
        },
        "line_items": [
            {
            "description": "Zava Ethiopia for Espresso",
            "quantity": 80,
            "unit_price": 20,
            "uom": "Kg",
            "total": 2000
            }
        ],
        "subtotal": 2000,
        "tax": 300,
        "shipping": 0,
        "total": 2300,
        "confidence": 0.88,
        "notes": "Handwritten PO (534) detected. Invoice # read as '100'. Invoice date read as 10/15/2025 and converted to ISO. Supplier address and purchaser/shipping address OCRed as 'Karlinska 1918, Karlin, Czechia' (minor uncertainty). Totals (subtotal 2000 + tax 300 + shipping 0 = total 2300) match the invoice."
        },   

    
    "00012": {
        "po_number": "888",
        "invoice_number": "00012",
        "invoice_date": "2205-10-01",
        "due_date": "2205-10-16",
        "currency": "USD",
        "supplier": {
            "name": "Contoso Fin Consulting",
            "address": "450 East 78th Ave, Denver, CO 12345",
            "email": "",
            "phone": "(123) 456-7890",
        },
        "bill_to": {
            "name": "Tomas Kubica",
            "address": "Karlinska 1918, Karlin, Czechia",
            "department": "",
        },
        "line_items": [
            {
                "description": "Consultation services implementation of AI powered grinder",
                "quantity": 3,
                "unit_price": 375,
                "uom": "hours",
                "total": 1125,
            },
        ],
        "subtotal": 1125,
        "tax": 0,
        "shipping": 0,
        "total": 1125,
        "confidence": 0.95,
        "notes": "Total matches the sum of line items.",
        "status": "pending",
    },
}


# ============================================================================
# Public API Functions
# ============================================================================


def check_po(po_number: str) -> POCheckResult:
    """Check if a purchase order number exists and is valid.
    
    Args:
        po_number: The purchase order number to check.
        
    Returns:
        POCheckResult with validation status.
    """
    po_upper = po_number.upper().strip()
    
    if po_upper in PURCHASE_ORDERS:
        po = PURCHASE_ORDERS[po_upper]
        status = po.get("status", "submitted")
        
        # Check if PO is in a valid state for invoicing
        if status in ["approved", "fulfilled"]:
            return POCheckResult(
                po_number=po_upper,
                exists=True,
                is_valid=True,
                message=f"PO {po_upper} exists and is valid for invoicing (status: {status})",
            )
        elif status == "cancelled":
            return POCheckResult(
                po_number=po_upper,
                exists=True,
                is_valid=False,
                message=f"PO {po_upper} exists but has been cancelled",
            )
        else:
            return POCheckResult(
                po_number=po_upper,
                exists=True,
                is_valid=False,
                message=f"PO {po_upper} exists but is not yet approved (status: {status})",
            )
    
    return POCheckResult(
        po_number=po_upper,
        exists=False,
        is_valid=False,
        message=f"PO {po_upper} does not exist in the system",
    )


def get_invoice(invoice_id: str) -> Optional[Invoice]:
    """Get invoice details by ID or invoice number.
    
    Args:
        invoice_id: The invoice ID or invoice number.
        
    Returns:
        Invoice details or None if not found.
    """
    # Normalize the ID
    inv_upper = invoice_id.upper().strip()
    
    # Try direct lookup by invoice number
    if inv_upper in INVOICES:
        inv_data = INVOICES[inv_upper]
        return Invoice(
            po_number=inv_data.get("po_number"),
            invoice_number=inv_data["invoice_number"],
            invoice_date=inv_data["invoice_date"],
            due_date=inv_data.get("due_date"),
            currency=inv_data["currency"],
            supplier=Supplier(**inv_data["supplier"]),
            bill_to=BillTo(**inv_data["bill_to"]) if inv_data.get("bill_to") else None,
            line_items=[LineItem(**item) for item in inv_data["line_items"]],
            subtotal=inv_data.get("subtotal"),
            tax=inv_data.get("tax"),
            shipping=inv_data.get("shipping"),
            total=inv_data["total"],
            confidence=inv_data.get("confidence"),
            notes=inv_data.get("notes"),
            status=inv_data.get("status", "pending"),
        )
    
    return None


def get_po(po_number: str) -> Optional[PurchaseOrder]:
    """Get purchase order details by PO number.
    
    Args:
        po_number: The purchase order number.
        
    Returns:
        PurchaseOrder details or None if not found.
    """
    po_upper = po_number.upper().strip()
    
    if po_upper in PURCHASE_ORDERS:
        po_data = PURCHASE_ORDERS[po_upper]
        return PurchaseOrder(
            po_number=po_data["po_number"],
            due_date=po_data.get("due_date"),
            currency=po_data["currency"],
            supplier=Supplier(**po_data["supplier"]),
            bill_to=BillTo(**po_data["bill_to"]) if po_data.get("bill_to") else None,
            line_items=[LineItem(**item) for item in po_data["line_items"]],
            subtotal=po_data.get("subtotal"),
            tax=po_data.get("tax"),
            shipping=po_data.get("shipping"),
            total=po_data["total"],
            confidence=po_data.get("confidence"),
            notes=po_data.get("notes"),
            status=po_data.get("status", "submitted"),
        )
    
    return None
