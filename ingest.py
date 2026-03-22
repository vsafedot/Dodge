import sqlite3
import json
import os
import glob

DB_PATH = "sap_o2c.db"
DATA_DIR = "sap-o2c-data"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop tables if they exist
    tables = [
        "sales_orders", "sales_order_items", "deliveries", "delivery_items",
        "billing_documents", "billing_items", "journal_entries"
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # Create tables
    cursor.execute("""
        CREATE TABLE sales_orders (
            salesOrder TEXT PRIMARY KEY,
            salesOrderType TEXT,
            creationDate TEXT,
            totalNetAmount REAL,
            transactionCurrency TEXT,
            soldToParty TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE sales_order_items (
            salesOrder TEXT,
            salesOrderItem TEXT,
            material TEXT,
            requestedQuantity REAL,
            requestedQuantityUnit TEXT,
            netAmount REAL,
            transactionCurrency TEXT,
            productionPlant TEXT,
            PRIMARY KEY (salesOrder, salesOrderItem)
        )
    """)
    cursor.execute("""
        CREATE TABLE deliveries (
            deliveryDocument TEXT PRIMARY KEY,
            deliveryDocumentType TEXT,
            creationDate TEXT,
            shippingPoint TEXT,
            overallGoodsMovementStatus TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE delivery_items (
            deliveryDocument TEXT,
            deliveryDocumentItem TEXT,
            actualDeliveryQuantity REAL,
            deliveryQuantityUnit TEXT,
            referenceSdDocument TEXT,
            referenceSdDocumentItem TEXT,
            plant TEXT,
            storageLocation TEXT,
            PRIMARY KEY (deliveryDocument, deliveryDocumentItem)
        )
    """)
    cursor.execute("""
        CREATE TABLE billing_documents (
            billingDocument TEXT PRIMARY KEY,
            billingDocumentType TEXT,
            creationDate TEXT,
            billingDocumentDate TEXT,
            totalNetAmount REAL,
            transactionCurrency TEXT,
            soldToParty TEXT,
            billingDocumentIsCancelled TEXT,
            accountingDocument TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE billing_items (
            billingDocument TEXT,
            billingDocumentItem TEXT,
            material TEXT,
            billingQuantity REAL,
            billingQuantityUnit TEXT,
            netAmount REAL,
            transactionCurrency TEXT,
            referenceSdDocument TEXT,
            referenceSdDocumentItem TEXT,
            PRIMARY KEY (billingDocument, billingDocumentItem)
        )
    """)
    cursor.execute("""
        CREATE TABLE journal_entries (
            accountingDocument TEXT,
            accountingDocumentItem TEXT,
            companyCode TEXT,
            fiscalYear TEXT,
            glAccount TEXT,
            glAccountType TEXT,
            customer TEXT,
            amountInTransactionCurrency REAL,
            transactionCurrency TEXT,
            postingDate TEXT,
            financialAccountType TEXT,
            clearingDate TEXT,
            clearingAccountingDocument TEXT
        )
    """)
    conn.commit()
    return conn

def ingest_jsonl(conn, folder, table_name, mapping_func):
    cursor = conn.cursor()
    files = glob.glob(os.path.join(DATA_DIR, folder, "*.jsonl"))
    for file in files:
        with open(file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                row = mapping_func(data)
                placeholders = ",".join(["?"] * len(row))
                try:
                    cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", row)
                except sqlite3.IntegrityError:
                    pass # Ignore duplicates if any
    conn.commit()

def safe_float(val):
    try:
        if val == "": return None
        return float(val)
    except (ValueError, TypeError):
        return None

def main():
    conn = init_db()
    
    print("Ingesting sales order headers...")
    ingest_jsonl(conn, "sales_order_headers", "sales_orders", lambda d: (
        d.get("salesOrder"), d.get("salesOrderType"), d.get("creationDate"), 
        safe_float(d.get("totalNetAmount")), d.get("transactionCurrency"), d.get("soldToParty")
    ))
    
    print("Ingesting sales order items...")
    ingest_jsonl(conn, "sales_order_items", "sales_order_items", lambda d: (
        d.get("salesOrder"), d.get("salesOrderItem"), d.get("material"), 
        safe_float(d.get("requestedQuantity")), d.get("requestedQuantityUnit"), 
        safe_float(d.get("netAmount")), d.get("transactionCurrency"), d.get("productionPlant")
    ))
    
    print("Ingesting delivery headers...")
    ingest_jsonl(conn, "outbound_delivery_headers", "deliveries", lambda d: (
        d.get("deliveryDocument"), d.get("deliveryDocumentType"), d.get("creationDate"), 
        d.get("shippingPoint"), d.get("overallGoodsMovementStatus")
    ))
    
    print("Ingesting delivery items...")
    ingest_jsonl(conn, "outbound_delivery_items", "delivery_items", lambda d: (
        d.get("deliveryDocument"), d.get("deliveryDocumentItem"), 
        safe_float(d.get("actualDeliveryQuantity")), d.get("deliveryQuantityUnit"), 
        d.get("referenceSdDocument"), d.get("referenceSdDocumentItem"),
        d.get("plant"), d.get("storageLocation")
    ))
    
    print("Ingesting billing headers...")
    ingest_jsonl(conn, "billing_document_headers", "billing_documents", lambda d: (
        d.get("billingDocument"), d.get("billingDocumentType"), d.get("creationDate"), 
        d.get("billingDocumentDate"), safe_float(d.get("totalNetAmount")), 
        d.get("transactionCurrency"), d.get("soldToParty"), 
        d.get("billingDocumentIsCancelled"), d.get("accountingDocument")
    ))
    
    print("Ingesting billing items...")
    ingest_jsonl(conn, "billing_document_items", "billing_items", lambda d: (
        d.get("billingDocument"), d.get("billingDocumentItem"), d.get("material"), 
        safe_float(d.get("billingQuantity")), d.get("billingQuantityUnit"), 
        safe_float(d.get("netAmount")), d.get("transactionCurrency"), 
        d.get("referenceSdDocument"), d.get("referenceSdDocumentItem")
    ))

    print("Ingesting journal entries...")
    ingest_jsonl(conn, "journal_entry_items_accounts_receivable", "journal_entries", lambda d: (
        d.get("accountingDocument"), d.get("accountingDocumentItem"), d.get("companyCode"),
        d.get("fiscalYear"), d.get("glAccount"), d.get("glAccountType"), d.get("customer"),
        safe_float(d.get("amountInTransactionCurrency")), d.get("transactionCurrency"),
        d.get("postingDate"), d.get("financialAccountType"), d.get("clearingDate"),
        d.get("clearingAccountingDocument")
    ))
    
    print("Creating indices for performance...")
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_soi_material ON sales_order_items(material)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_di_ref ON delivery_items(referenceSdDocument, referenceSdDocumentItem)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bi_ref ON billing_items(referenceSdDocument, referenceSdDocumentItem)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bd_acct ON billing_documents(accountingDocument)")
    
    print("Ingestion complete!")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
