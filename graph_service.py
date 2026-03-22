import sqlite3

DB_PATH = "sap_o2c.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_full_graph(limit=None):
    conn = get_db()
    cursor = conn.cursor()
    
    nodes = []
    edges = []
    
    added_nodes = set()
    def add_node(n_id, n_label, n_group, props=None):
        if n_id and n_id not in added_nodes:
            added_nodes.add(n_id)
            nodes.append({"id": n_id, "label": n_label, "group": n_group, **(props or {})})
            
    def add_edge(source, target, label):
        if source and target:
            edges.append({"source": source, "target": target, "label": label})

    # Get a set of recent Sales Orders
    if limit is not None:
        so_rows = cursor.execute("SELECT * FROM sales_orders LIMIT ?", (limit,)).fetchall()
    else:
        so_rows = cursor.execute("SELECT * FROM sales_orders").fetchall()
    
    for so in so_rows:
        so_id = f"SO-{so['salesOrder']}"
        customer_id = f"CUST-{so['soldToParty']}"
        add_node(so_id, so['salesOrder'], "SalesOrder", {"amount": so['totalNetAmount'], "date": so['creationDate']})
        add_node(customer_id, so['soldToParty'], "Customer")
        add_edge(customer_id, so_id, "PLACED")
        
        # Get items
        item_rows = cursor.execute("SELECT * FROM sales_order_items WHERE salesOrder=?", (so['salesOrder'],)).fetchall()
        for item in item_rows:
            item_id = f"SOI-{item['salesOrder']}-{item['salesOrderItem']}"
            product_id = f"PROD-{item['material']}"
            add_node(item_id, item['salesOrderItem'], "SalesOrderItem", {"qty": item['requestedQuantity']})
            add_node(product_id, item['material'], "Product")
            add_edge(so_id, item_id, "HAS_ITEM")
            add_edge(item_id, product_id, "CONTAINS")
            
            # Find delivery items for this SO item
            del_item_rows = cursor.execute("SELECT * FROM delivery_items WHERE referenceSdDocument=? AND referenceSdDocumentItem=?", (item['salesOrder'], item['salesOrderItem'])).fetchall()
            for di in del_item_rows:
                del_id = f"DEL-{di['deliveryDocument']}"
                del_item_id = f"DELI-{di['deliveryDocument']}-{di['deliveryDocumentItem']}"
                # Get delivery header
                del_row = cursor.execute("SELECT * FROM deliveries WHERE deliveryDocument=?", (di['deliveryDocument'],)).fetchone()
                if del_row:
                    add_node(del_id, del_row['deliveryDocument'], "Delivery", {"date": del_row['creationDate']})
                
                add_node(del_item_id, di['deliveryDocumentItem'], "DeliveryItem", {"qty": di['actualDeliveryQuantity']})
                add_edge(del_id, del_item_id, "HAS_ITEM")
                add_edge(item_id, del_item_id, "DELIVERED_IN")
                
                # Find billing items for this delivery
                bill_item_rows = cursor.execute("SELECT * FROM billing_items WHERE referenceSdDocument=? AND referenceSdDocumentItem=?", (di['deliveryDocument'], di['deliveryDocumentItem'])).fetchall()
                for bi in bill_item_rows:
                    bill_id = f"INV-{bi['billingDocument']}"
                    bill_item_id = f"INVI-{bi['billingDocument']}-{bi['billingDocumentItem']}"
                    
                    bill_row = cursor.execute("SELECT * FROM billing_documents WHERE billingDocument=?", (bi['billingDocument'],)).fetchone()
                    if bill_row:
                        add_node(bill_id, bill_row['billingDocument'], "Invoice", {"amount": bill_row['totalNetAmount']})
                        
                        # Link Invoice to Journal Entry
                        if bill_row['accountingDocument']:
                            je_rows = cursor.execute("SELECT * FROM journal_entries WHERE accountingDocument=?", (bill_row['accountingDocument'],)).fetchall()
                            for je in je_rows:
                                je_id = f"JE-{je['accountingDocument']}-{je['accountingDocumentItem']}"
                                add_node(je_id, je['accountingDocument'], "JournalEntry", {"amount": je['amountInTransactionCurrency']})
                                add_edge(bill_id, je_id, "HAS_PAYMENT")
                    
                    add_node(bill_item_id, bi['billingDocumentItem'], "InvoiceItem", {"qty": bi['billingQuantity'], "amount": bi['netAmount']})
                    add_edge(bill_id, bill_item_id, "HAS_ITEM")
                    add_edge(del_item_id, bill_item_id, "BILLED_IN")

    conn.close()
    return {"nodes": nodes, "edges": edges}

def get_subgraph_by_id(node_id: str):
    return get_full_graph(limit=10)
