import sqlite3
import os
import json
from groq import Groq

DB_PATH = "sap_o2c.db"

def get_schema():
    return """
        Table: sales_orders (salesOrder, salesOrderType, creationDate, totalNetAmount, transactionCurrency, soldToParty)
        Table: sales_order_items (salesOrder, salesOrderItem, material, requestedQuantity, requestedQuantityUnit, netAmount, transactionCurrency, productionPlant)
        Table: deliveries (deliveryDocument, deliveryDocumentType, creationDate, shippingPoint, overallGoodsMovementStatus)
        Table: delivery_items (deliveryDocument, deliveryDocumentItem, actualDeliveryQuantity, deliveryQuantityUnit, referenceSdDocument, referenceSdDocumentItem, plant, storageLocation)
        Table: billing_documents (billingDocument, billingDocumentType, creationDate, billingDocumentDate, totalNetAmount, transactionCurrency, soldToParty, billingDocumentIsCancelled, accountingDocument)
        Table: billing_items (billingDocument, billingDocumentItem, material, billingQuantity, billingQuantityUnit, netAmount, transactionCurrency, referenceSdDocument, referenceSdDocumentItem)
        Table: journal_entries (accountingDocument, accountingDocumentItem, companyCode, fiscalYear, glAccount, glAccountType, customer, amountInTransactionCurrency, transactionCurrency, postingDate, financialAccountType, clearingDate, clearingAccountingDocument)
        
        Note:
        - sales_order_items links to delivery_items via delivery_items.referenceSdDocument = sales_order_items.salesOrder AND delivery_items.referenceSdDocumentItem = sales_order_items.salesOrderItem
        - delivery_items links to billing_items via billing_items.referenceSdDocument = delivery_items.deliveryDocument AND billing_items.referenceSdDocumentItem = delivery_items.deliveryDocumentItem
        - billing_documents links to journal_entries via journal_entries.accountingDocument = billing_documents.accountingDocument
    """

def query_database(sql):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [description[0] if description else "col" for description in cursor.description] if cursor.description else []
        results = [dict(zip(columns, row)) for row in rows]
        return results, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()

import re

def handle_chat_query(user_query: str):
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        try:
            with open("api.txt", "r") as f:
                api_key = f.read().strip()
        except Exception:
            pass

    if not api_key:
        return "I need a Groq API Key to answer that! Please provide api.txt or set GROQ_API_KEY."
    
    client = Groq(api_key=api_key)
    schema = get_schema()
    
    prompt = f"""
    You are an expert SQL assistant for an SAP Order to Cash SQLite database.
    Your goal is to parse the user's question and output exactly ONE valid SQL query to answer it.
    
    CRITICAL INSTRUCTION: Your entire response MUST be the raw SQL query. Do NOT output any markdown, explanations, or backticks (no ```). Start your response directly with the SQL keyword (e.g., SELECT).
    
    Here is the schema:
    {schema}
    
    User question: {user_query}
    """
    
    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        
        # Robustly extract SQL
        match = re.search(r'```(?:sql)?\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
        if match:
            sql_query = match.group(1).strip()
        else:
            sql_query = content.replace('```sql', '').replace('```', '').strip()
            idx = sql_query.upper().find('SELECT')
            if idx != -1:
                sql_query = sql_query[idx:]
        
        results, error = query_database(sql_query)
        if error:
             return "I'm sorry, I couldn't process this request. Please try rephrasing your question."
        
        final_prompt = f"""
        User Question: {user_query}
        Data Results Retrieved: {json.dumps(results[:100])}
        
        Provide a precise, highly professional, and natural answer to the user's question based on these Data Results.
        
        SECURITY CONSTRAINTS:
        1. NEVER mention SQL, databases, tables, schemas, backend logic, or internal queries.
        2. Act as a seamless business intelligence assistant. Simply state the facts.
        
        UX GUIDELINES:
        - If the results contain multiple records, format them beautifully using a Markdown table.
        - Give a precise answer. If the results are empty, just say nicely that no relevant records match their request.
        """
        final_response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.3
        )
        return final_response.choices[0].message.content
        
    except Exception as e:
        return f"Error connecting to LLM: {str(e)}"
