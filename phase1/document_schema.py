"""
Phase 1 — Script 2: Generate schema documentation for embedding.

This script introspects the Northwind database and produces structured
plain-English documents for every table. These documents become the
knowledge base your RAG system retrieves from.

Run: python phase1/2_document_schema.py
Output: data/schema_docs.json
"""

import json
import os
from sqlalchemy import create_engine, inspect, text
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL", "postgresql://localhost:5432/northwind")

# ---------------------------------------------------------------------------
# Hand-written table descriptions (the part that takes analyst judgment)
# The richer these are, the better your RAG retrieval will be.
# Update/extend these with your own domain knowledge.
# ---------------------------------------------------------------------------
TABLE_DOCS = {
    "customers": {
        "description": (
            "Stores information about all customers who have placed orders. "
            "Each customer has a unique 5-character ID. Use this table to answer "
            "questions about who our customers are, where they are located, and "
            "how to contact them."
        ),
        "business_meaning": (
            "A 'customer' is any company or individual that has purchased from us. "
            "CustomerID is used as a foreign key in the Orders table."
        ),
        "common_use_cases": [
            "Count total number of customers",
            "Find customers in a specific country or city",
            "Look up contact details for a customer",
            "Identify customers who have never ordered (LEFT JOIN with orders)",
        ],
        "columns": {
            "customer_id": "Unique 5-character identifier for the customer (e.g. 'ALFKI')",
            "company_name": "Name of the customer's company",
            "contact_name": "Full name of the primary contact person at the company",
            "contact_title": "Job title of the contact person (e.g. 'Sales Representative')",
            "address": "Street address of the customer",
            "city": "City where the customer is located",
            "region": "State, province, or region (may be NULL for non-US/Canada)",
            "postal_code": "ZIP or postal code",
            "country": "Country of the customer",
            "phone": "Customer phone number",
            "fax": "Customer fax number (often NULL)",
        },
    },
    "orders": {
        "description": (
            "Records every order placed by customers. This is the central fact table "
            "for sales analysis. Each row is one order. To get order line items, join "
            "with order_details. To get revenue, join order_details and multiply "
            "unit_price by quantity with freight."
        ),
        "business_meaning": (
            "An 'order' is a single transaction from a customer. Orders have a status "
            "implied by their dates: if shipped_date is NULL, the order has not shipped yet."
        ),
        "common_use_cases": [
            "Total orders per month or year",
            "Orders that have not yet shipped",
            "Average days between order_date and shipped_date (fulfillment time)",
            "Orders by employee (sales attribution)",
            "Orders shipped to a specific country or region",
        ],
        "columns": {
            "order_id": "Unique integer identifier for the order",
            "customer_id": "Foreign key to customers.customer_id",
            "employee_id": "Foreign key to employees.employee_id — who took the order",
            "order_date": "Date the order was placed by the customer",
            "required_date": "Date the customer requested delivery by",
            "shipped_date": "Date the order actually shipped. NULL if not yet shipped.",
            "ship_via": "Foreign key to shippers.shipper_id — which shipping company was used",
            "freight": "Shipping cost for this order in USD",
            "ship_name": "Name of the shipping recipient (may differ from customer name)",
            "ship_address": "Delivery street address",
            "ship_city": "Delivery city",
            "ship_region": "Delivery region or state",
            "ship_postal_code": "Delivery postal code",
            "ship_country": "Delivery country",
        },
    },
    "order_details": {
        "description": (
            "Line items for each order — one row per product per order. "
            "To calculate revenue for an order: SUM(unit_price * quantity * (1 - discount)). "
            "Always join with orders to filter by date range."
        ),
        "business_meaning": (
            "This is the bridge table between orders and products. "
            "Revenue analysis almost always requires this table."
        ),
        "common_use_cases": [
            "Total revenue for a date range: JOIN orders ON order_id, SUM(unit_price * quantity * (1-discount))",
            "Best-selling products by quantity or revenue",
            "Average order value",
            "Products frequently bought together",
        ],
        "columns": {
            "order_id": "Foreign key to orders.order_id",
            "product_id": "Foreign key to products.product_id",
            "unit_price": "Price per unit at time of order (may differ from current products.unit_price)",
            "quantity": "Number of units ordered",
            "discount": "Fractional discount applied (0.0 = no discount, 0.1 = 10% off). Subtract from 1 to get the multiplier.",
        },
    },
    "products": {
        "description": (
            "The product catalog — one row per product. Contains current pricing "
            "and inventory levels. For historical prices, use order_details.unit_price. "
            "Products belong to a category and are supplied by a single supplier."
        ),
        "business_meaning": "A 'product' is a SKU we sell. discontinued=1 means we no longer sell it.",
        "common_use_cases": [
            "List all products in a category",
            "Find products with low stock (units_in_stock < reorder_level)",
            "Products that are discontinued",
            "Most expensive products",
        ],
        "columns": {
            "product_id": "Unique integer identifier for the product",
            "product_name": "Name of the product",
            "supplier_id": "Foreign key to suppliers.supplier_id",
            "category_id": "Foreign key to categories.category_id",
            "quantity_per_unit": "Description of packaging (e.g. '12 - 550 ml bottles')",
            "unit_price": "Current list price in USD",
            "units_in_stock": "Current inventory on hand",
            "units_on_order": "Units ordered from supplier but not yet received",
            "reorder_level": "Inventory threshold that triggers a reorder",
            "discontinued": "1 if product is no longer sold, 0 if active",
        },
    },
    "categories": {
        "description": (
            "Product categories (e.g. Beverages, Condiments, Seafood). "
            "Each product belongs to exactly one category."
        ),
        "business_meaning": "Top-level grouping for products. Useful for category-level sales rollups.",
        "common_use_cases": [
            "Revenue by category",
            "Number of products per category",
            "Best-selling category",
        ],
        "columns": {
            "category_id": "Unique integer identifier",
            "category_name": "Name of the category (e.g. 'Beverages', 'Dairy Products')",
            "description": "Short description of what kinds of products belong here",
        },
    },
    "employees": {
        "description": (
            "Company employees, particularly the sales reps who take orders. "
            "Each order is attributed to one employee. Employees can have a manager "
            "(reports_to references another employee_id)."
        ),
        "business_meaning": "Used for sales attribution and performance analysis.",
        "common_use_cases": [
            "Sales (revenue) by employee",
            "Number of orders per employee",
            "Employee hierarchy (who reports to whom)",
            "Top performing sales reps",
        ],
        "columns": {
            "employee_id": "Unique integer identifier",
            "last_name": "Employee's last name",
            "first_name": "Employee's first name",
            "title": "Job title (e.g. 'Sales Representative', 'Vice President, Sales')",
            "birth_date": "Date of birth",
            "hire_date": "Date the employee was hired",
            "city": "City where the employee is based",
            "country": "Country where the employee is based",
            "reports_to": "employee_id of this employee's manager (NULL for top-level)",
        },
    },
    "suppliers": {
        "description": (
            "Companies that supply products to us. Each product has one supplier. "
            "Suppliers are external vendors, not customers."
        ),
        "business_meaning": "Used for procurement and vendor analysis.",
        "common_use_cases": [
            "Products supplied by a given vendor",
            "Number of products per supplier",
            "Suppliers by country",
        ],
        "columns": {
            "supplier_id": "Unique integer identifier",
            "company_name": "Name of the supplier company",
            "contact_name": "Primary contact at the supplier",
            "country": "Country where the supplier is based",
            "phone": "Supplier phone number",
        },
    },
    "shippers": {
        "description": "Shipping companies used to deliver orders (e.g. FedEx, UPS equivalents).",
        "business_meaning": "Used to analyse which carrier is used most and freight cost by carrier.",
        "common_use_cases": [
            "Orders per shipper",
            "Average freight cost per shipper",
        ],
        "columns": {
            "shipper_id": "Unique integer identifier",
            "company_name": "Name of the shipping company",
            "phone": "Shipper contact phone",
        },
    },
}

# ---------------------------------------------------------------------------
# Business glossary — plain-English definitions of key terms users will use
# ---------------------------------------------------------------------------
GLOSSARY = [
    {
        "term": "Revenue",
        "definition": (
            "Total sales value. Calculate as: "
            "SUM(order_details.unit_price * order_details.quantity * (1 - order_details.discount)). "
            "Always join order_details with orders to apply date filters."
        ),
    },
    {
        "term": "Gross revenue vs net revenue",
        "definition": (
            "Gross revenue ignores discounts: SUM(unit_price * quantity). "
            "Net revenue applies discounts: SUM(unit_price * quantity * (1 - discount))."
        ),
    },
    {
        "term": "Average order value (AOV)",
        "definition": (
            "Total revenue divided by number of orders. "
            "Requires joining orders, order_details. Group by order_id first, then average."
        ),
    },
    {
        "term": "Fulfillment time",
        "definition": (
            "Number of days between order_date and shipped_date in the orders table. "
            "Calculate with: shipped_date - order_date."
        ),
    },
    {
        "term": "Active product",
        "definition": "A product where products.discontinued = 0.",
    },
    {
        "term": "Unshipped orders",
        "definition": "Orders where orders.shipped_date IS NULL.",
    },
    {
        "term": "YTD (year to date)",
        "definition": (
            "Filter orders.order_date where EXTRACT(year FROM order_date) = <year>. "
            "The data in Northwind runs from 1996 to 1998."
        ),
    },
]

# ---------------------------------------------------------------------------
# Sample Q&A pairs — ground truth for your eval set later
# ---------------------------------------------------------------------------
SAMPLE_QUERIES = [
    {
        "question": "What is total revenue for 1997?",
        "sql": """
            SELECT ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS revenue_1997
            FROM order_details od
            JOIN orders o ON od.order_id = o.order_id
            WHERE EXTRACT(year FROM o.order_date) = 1997;
        """,
        "note": "Use net revenue (discount applied). Filter on order_date year.",
    },
    {
        "question": "Who are the top 5 customers by revenue?",
        "sql": """
            SELECT c.company_name,
                   ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS revenue
            FROM order_details od
            JOIN orders o ON od.order_id = o.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY c.company_name
            ORDER BY revenue DESC
            LIMIT 5;
        """,
        "note": "Always use net revenue. Group by company.",
    },
    {
        "question": "What are the best-selling product categories by quantity?",
        "sql": """
            SELECT cat.category_name, SUM(od.quantity) AS total_qty
            FROM order_details od
            JOIN products p ON od.product_id = p.product_id
            JOIN categories cat ON p.category_id = cat.category_id
            GROUP BY cat.category_name
            ORDER BY total_qty DESC;
        """,
        "note": "Join order_details → products → categories.",
    },
    {
        "question": "Which employee has generated the most revenue?",
        "sql": """
            SELECT e.first_name || ' ' || e.last_name AS employee,
                   ROUND(SUM(od.unit_price * od.quantity * (1 - od.discount))::numeric, 2) AS revenue
            FROM order_details od
            JOIN orders o ON od.order_id = o.order_id
            JOIN employees e ON o.employee_id = e.employee_id
            GROUP BY employee
            ORDER BY revenue DESC
            LIMIT 1;
        """,
        "note": "Attribution via orders.employee_id.",
    },
    {
        "question": "How many orders are still unshipped?",
        "sql": """
            SELECT COUNT(*) AS unshipped_orders
            FROM orders
            WHERE shipped_date IS NULL;
        """,
        "note": "Unshipped = shipped_date IS NULL.",
    },
]


def get_db_metadata(engine):
    """Pull column types and nullable flags from the live DB."""
    inspector = inspect(engine)
    meta = {}
    for table_name in inspector.get_table_names():
        cols = inspector.get_columns(table_name)
        meta[table_name] = {
            col["name"]: {
                "type": str(col["type"]),
                "nullable": col["nullable"],
            }
            for col in cols
        }
    return meta


def build_documents(engine):
    """Combine hand-written docs with live DB metadata into embeddable chunks."""
    db_meta = get_db_metadata(engine)
    documents = []

    # --- Table documents ---
    for table_name, doc in TABLE_DOCS.items():
        col_lines = []
        for col_name, col_desc in doc["columns"].items():
            db_info = db_meta.get(table_name, {}).get(col_name, {})
            type_str = db_info.get("type", "unknown")
            nullable = "nullable" if db_info.get("nullable", True) else "NOT NULL"
            col_lines.append(f"  - {col_name} ({type_str}, {nullable}): {col_desc}")

        use_cases = "\n".join(f"  • {u}" for u in doc["common_use_cases"])
        col_block = "\n".join(col_lines)

        content = f"""TABLE: {table_name}

DESCRIPTION:
{doc['description']}

BUSINESS MEANING:
{doc['business_meaning']}

COLUMNS:
{col_block}

COMMON USE CASES:
{use_cases}
"""
        documents.append({
            "id": f"table_{table_name}",
            "type": "table_description",
            "table": table_name,
            "content": content.strip(),
        })

    # --- Glossary documents ---
    for item in GLOSSARY:
        content = f"TERM: {item['term']}\n\nDEFINITION: {item['definition']}"
        documents.append({
            "id": f"glossary_{item['term'].lower().replace(' ', '_')}",
            "type": "glossary",
            "content": content.strip(),
        })

    # --- Sample Q&A documents ---
    for i, qa in enumerate(SAMPLE_QUERIES):
        content = f"""EXAMPLE QUERY {i+1}

QUESTION: {qa['question']}

SQL:
{qa['sql'].strip()}

NOTE: {qa['note']}
"""
        documents.append({
            "id": f"example_query_{i+1}",
            "type": "example_query",
            "content": content.strip(),
        })

    return documents


def main():
    print("=== Phase 1 / Step 2: Generating Schema Documentation ===\n")

    engine = create_engine(DB_URL)

    print("1. Introspecting database...")
    documents = build_documents(engine)
    print(f"   Built {len(documents)} documents:")
    for doc_type in ["table_description", "glossary", "example_query"]:
        n = sum(1 for d in documents if d["type"] == doc_type)
        print(f"     {doc_type:<25} {n} docs")

    os.makedirs("data", exist_ok=True)
    out_path = "data/schema_docs.json"
    with open(out_path, "w") as f:
        json.dump(documents, f, indent=2)

    print(f"\n2. Saved to {out_path}")
    print(f"   Total characters across all docs: {sum(len(d['content']) for d in documents):,}")
    print("\n✅ Schema documentation complete.")
    print("   Next: run python phase1/3_embed_and_store.py")


if __name__ == "__main__":
    main()