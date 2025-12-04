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
        "invoice_number": "100010101010",
        "invoice_date": "2025-10-15",
        "due_date": None,
        "currency": "EUR",
        "supplier": {
            "name": "Zava Specialty Coffee",
            "address": "333 3rd Ave, Seattle, WA 12345",
            "email": None,
            "phone": "123-456-7890",
        },
        "bill_to": {
            "name": "Tomas Kubica",
            "address": "Karlinska 1918, Karlin, Czechia",
            "department": "Cofilot Inc",
        },
        "line_items": [
            {"description": "Zava Ethiopia for Espresso", "quantity": 80, "unit_price": 20, "uom": "Kg", "total": 2000},
        ],
        "subtotal": 2000,
        "tax": 300,
        "shipping": 0,
        "total": 2300,
        "confidence": 0.95,
        "notes": "",
        "status": "approved",
    },
    "PO-2024-002": {
        "po_number": "PO-2024-002",
        "invoice_number": "INV-OFS-2024-0210",
        "invoice_date": "2024-02-10",
        "due_date": "2024-03-10",
        "currency": "EUR",
        "supplier": {
            "name": "Office Furniture Solutions",
            "address": "Möbelweg 15, 80331 Munich, Germany",
            "email": "sales@office-furniture.de",
            "phone": "+49 89 123 4567",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "Facilities",
        },
        "line_items": [
            {"description": "Ergonomic Office Chair", "quantity": 5, "unit_price": 600.00, "uom": "unit", "total": 3000.00},
            {"description": "Standing Desk Converter", "quantity": 3, "unit_price": 500.00, "uom": "unit", "total": 1500.00},
        ],
        "subtotal": 4500.00,
        "tax": 855.00,
        "shipping": 150.00,
        "total": 5505.00,
        "confidence": 0.92,
        "notes": "New employee workstation setup",
        "status": "approved",
    },
    "PO-2024-003": {
        "po_number": "PO-2024-003",
        "invoice_number": "INV-TEQ-2024-0305",
        "invoice_date": "2024-03-05",
        "due_date": "2024-04-05",
        "currency": "EUR",
        "supplier": {
            "name": "Tech Equipment AG",
            "address": "Technologiepark 8, 8005 Zurich, Switzerland",
            "email": "enterprise@tech-equipment.ch",
            "phone": "+41 44 567 8901",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "IT",
        },
        "line_items": [
            {"description": "MacBook Pro 14-inch", "quantity": 2, "unit_price": 2500.00, "uom": "unit", "total": 5000.00},
            {"description": "External Monitor 27-inch", "quantity": 3, "unit_price": 450.00, "uom": "unit", "total": 1350.00},
            {"description": "Wireless Keyboard and Mouse Set", "quantity": 5, "unit_price": 120.00, "uom": "set", "total": 600.00},
            {"description": "USB-C Docking Station", "quantity": 3, "unit_price": 200.00, "uom": "unit", "total": 600.00},
            {"description": "Laptop Bags", "quantity": 2, "unit_price": 100.00, "uom": "unit", "total": 200.00},
        ],
        "subtotal": 7750.00,
        "tax": 596.75,
        "shipping": 0.00,
        "total": 8346.75,
        "confidence": 0.98,
        "notes": "Q1 IT equipment refresh",
        "status": "fulfilled",
    },
    "PO-2024-004": {
        "po_number": "PO-2024-004",
        "invoice_number": "INV-MML-2024-0315",
        "invoice_date": "2024-03-15",
        "due_date": "2024-04-15",
        "currency": "EUR",
        "supplier": {
            "name": "Marketing Materials Ltd",
            "address": "Print Street 22, 11000 Prague, Czech Republic",
            "email": "info@marketing-materials.cz",
            "phone": "+420 222 333 444",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "Marketing",
        },
        "line_items": [
            {"description": "Business Cards (500 pcs)", "quantity": 10, "unit_price": 50.00, "uom": "box", "total": 500.00},
            {"description": "Brochures (1000 pcs)", "quantity": 2, "unit_price": 250.00, "uom": "box", "total": 500.00},
            {"description": "Promotional Banners", "quantity": 2, "unit_price": 100.00, "uom": "unit", "total": 200.00},
        ],
        "subtotal": 1200.00,
        "tax": 252.00,
        "shipping": 45.00,
        "total": 1497.00,
        "confidence": 0.88,
        "notes": "Trade show materials",
        "status": "submitted",
    },
    "PO-2024-005": {
        "po_number": "PO-2024-005",
        "invoice_number": "INV-CSV-2024-0401",
        "invoice_date": "2024-04-01",
        "due_date": "2024-04-15",
        "currency": "EUR",
        "supplier": {
            "name": "Catering Services Vienna",
            "address": "Gourmetgasse 5, 1030 Vienna, Austria",
            "email": "events@catering-vienna.at",
            "phone": "+43 1 987 6543",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "HR",
        },
        "line_items": [
            {"description": "Corporate Event Catering (50 people)", "quantity": 1, "unit_price": 3000.00, "uom": "event", "total": 3000.00},
        ],
        "subtotal": 3000.00,
        "tax": 300.00,
        "shipping": 0.00,
        "total": 3300.00,
        "confidence": 0.91,
        "notes": "Company anniversary celebration - CANCELLED due to venue change",
        "status": "cancelled",
    },
}

INVOICES = {
    "INV-2024-0001": {
        "po_number": "PO-2024-001",
        "invoice_number": "INV-2024-0001",
        "invoice_date": "2024-02-05",
        "due_date": "2024-03-05",
        "currency": "EUR",
        "supplier": {
            "name": "Coffee Supplies GmbH",
            "address": "Kaffeestraße 42, 1010 Vienna, Austria",
            "email": "orders@coffee-supplies.at",
            "phone": "+43 1 234 5678",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "Operations",
        },
        "line_items": [
            {"description": "Premium Arabica Coffee Beans (10kg)", "quantity": 5, "unit_price": 350.00, "uom": "bag", "total": 1750.00},
            {"description": "Coffee Filters (500 pack)", "quantity": 10, "unit_price": 25.00, "uom": "pack", "total": 250.00},
            {"description": "Cleaning Supplies", "quantity": 1, "unit_price": 500.00, "uom": "set", "total": 500.00},
        ],
        "subtotal": 2500.00,
        "tax": 500.00,
        "shipping": 0.00,
        "total": 3000.00,
        "confidence": 0.97,
        "notes": "Payment received on 2024-02-28",
        "status": "paid",
    },
    "INV-2024-0002": {
        "po_number": "PO-2024-002",
        "invoice_number": "INV-2024-0002",
        "invoice_date": "2024-03-10",
        "due_date": "2024-04-10",
        "currency": "EUR",
        "supplier": {
            "name": "Office Furniture Solutions",
            "address": "Möbelweg 15, 80331 Munich, Germany",
            "email": "sales@office-furniture.de",
            "phone": "+49 89 123 4567",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "Facilities",
        },
        "line_items": [
            {"description": "Ergonomic Office Chair", "quantity": 5, "unit_price": 600.00, "uom": "unit", "total": 3000.00},
            {"description": "Standing Desk Converter", "quantity": 3, "unit_price": 500.00, "uom": "unit", "total": 1500.00},
        ],
        "subtotal": 4500.00,
        "tax": 900.00,
        "shipping": 0.00,
        "total": 5400.00,
        "confidence": 0.94,
        "notes": "Approved for payment",
        "status": "approved",
    },
    "INV-2024-0003": {
        "po_number": "PO-2024-003",
        "invoice_number": "INV-2024-0003",
        "invoice_date": "2024-03-25",
        "due_date": "2024-04-25",
        "currency": "EUR",
        "supplier": {
            "name": "Tech Equipment AG",
            "address": "Technologiepark 8, 8005 Zurich, Switzerland",
            "email": "enterprise@tech-equipment.ch",
            "phone": "+41 44 567 8901",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "IT",
        },
        "line_items": [
            {"description": "MacBook Pro 14-inch", "quantity": 2, "unit_price": 2500.00, "uom": "unit", "total": 5000.00},
            {"description": "External Monitor 27-inch", "quantity": 3, "unit_price": 450.00, "uom": "unit", "total": 1350.00},
            {"description": "Wireless Keyboard and Mouse Set", "quantity": 5, "unit_price": 120.00, "uom": "set", "total": 600.00},
            {"description": "USB-C Docking Station", "quantity": 3, "unit_price": 200.00, "uom": "unit", "total": 600.00},
            {"description": "Laptop Bags", "quantity": 2, "unit_price": 100.00, "uom": "unit", "total": 200.00},
        ],
        "subtotal": 7750.00,
        "tax": 1550.00,
        "shipping": 0.00,
        "total": 9300.00,
        "confidence": 0.96,
        "notes": "Awaiting manager approval",
        "status": "pending",
    },
    "INV-2024-0004": {
        "po_number": None,
        "invoice_number": "INV-2024-0004",
        "invoice_date": "2024-04-01",
        "due_date": "2024-05-01",
        "currency": "EUR",
        "supplier": {
            "name": "Consulting Partners s.r.o.",
            "address": "Václavské náměstí 12, 11000 Prague, Czech Republic",
            "email": "billing@consulting-partners.cz",
            "phone": "+420 222 111 333",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "Strategy",
        },
        "line_items": [
            {"description": "Strategic Consulting Services - March 2024", "quantity": 40, "unit_price": 375.00, "uom": "hour", "total": 15000.00},
        ],
        "subtotal": 15000.00,
        "tax": 3000.00,
        "shipping": 0.00,
        "total": 18000.00,
        "confidence": 0.89,
        "notes": "No PO on file - requires special approval",
        "status": "pending",
    },
    "INV-2024-0005": {
        "po_number": "PO-2024-099",
        "invoice_number": "INV-2024-0005",
        "invoice_date": "2024-04-05",
        "due_date": "2024-04-20",
        "currency": "EUR",
        "supplier": {
            "name": "Cloud Services Provider",
            "address": "Cloud Street 1, 10115 Berlin, Germany",
            "email": "invoices@cloud-provider.de",
            "phone": "+49 30 555 1234",
        },
        "bill_to": {
            "name": "Acme Corporation",
            "address": "Hauptstraße 100, 1020 Vienna, Austria",
            "department": "IT",
        },
        "line_items": [
            {"description": "Cloud Hosting - April 2024", "quantity": 1, "unit_price": 2400.00, "uom": "month", "total": 2400.00},
        ],
        "subtotal": 2400.00,
        "tax": 480.00,
        "shipping": 0.00,
        "total": 2880.00,
        "confidence": 0.93,
        "notes": "Rejected - PO number does not exist in system",
        "status": "rejected",
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
        status = po["status"]
        
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
            invoice_number=po_data["invoice_number"],
            invoice_date=po_data["invoice_date"],
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
