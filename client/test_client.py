#!/usr/bin/env python3
"""
Test Client for Invoice Service
Demonstrates how to use the gRPC Invoice Service
"""

import sys
import time
from typing import Any, cast
import grpc

# Make sure generated stubs are importable when run as script or in Docker.
sys.path.insert(0, "./app")
sys.path.insert(0, "/app/app")

from generated import invoice_pb2
from generated import invoice_pb2_grpc

PB2 = cast(Any, invoice_pb2)


class InvoiceClient:
    """Client for the gRPC Invoice Service"""
    
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = invoice_pb2_grpc.InvoiceServiceStub(self.channel)
    
    def create_invoice(self, invoice_id: str, supplier: str, amount: float):
        """Create a new invoice"""
        print(f"\n Creating invoice: {invoice_id}")
        try:
            request = PB2.CreateInvoiceRequest(
                id=invoice_id,
                supplier=supplier,
                amount=amount
            )
            response = self.stub.CreateInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            print(f"   Invoice: {response.invoice.id}")
            print(f"   Supplier: {response.invoice.supplier}")
            print(f"   Amount: {response.invoice.amount}€")
            return response.invoice
        except grpc.RpcError as e:
            print(f"❌ Error: {e.details()}")
            return None
    
    def get_invoice(self, invoice_id: str):
        """Get an invoice by ID"""
        print(f"\n Getting invoice: {invoice_id}")
        try:
            request = PB2.GetInvoiceRequest(id=invoice_id)
            response = self.stub.GetInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            print(f"   ID: {response.invoice.id}")
            print(f"   Supplier: {response.invoice.supplier}")
            print(f"   Amount: {response.invoice.amount}€")
            print(f"   Status: {response.invoice.status}")
            return response.invoice
        except grpc.RpcError as e:
            print(f"❌ Error: {e.details()}")
            return None
    
    def list_invoices(self, skip=0, limit=10):
        """List all invoices"""
        print(f"\n Listing invoices (skip={skip}, limit={limit})")
        try:
            request = PB2.ListInvoicesRequest(skip=skip, limit=limit)
            response = self.stub.ListInvoices(request, timeout=5)
            print(f"✅ Found {len(response.invoices)} invoices (total: {response.total})")
            for inv in response.invoices:
                print(f"   - {inv.id}: {inv.supplier} ({inv.amount}€) - {inv.status}")
            return response.invoices
        except grpc.RpcError as e:
            print(f"❌ Error: {e.details()}")
            return []
    
    def update_invoice(self, invoice_id: str, supplier: str, amount: float):
        """Update an invoice"""
        print(f"\n Updating invoice: {invoice_id}")
        try:
            request = PB2.UpdateInvoiceRequest(
                id=invoice_id,
                supplier=supplier,
                amount=amount
            )
            response = self.stub.UpdateInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            print(f"   New Amount: {response.invoice.amount}€")
            return response.invoice
        except grpc.RpcError as e:
            print(f"❌ Error: {e.details()}")
            return None
    
    def delete_invoice(self, invoice_id: str):
        """Delete an invoice"""
        print(f"\n Deleting invoice: {invoice_id}")
        try:
            request = PB2.DeleteInvoiceRequest(id=invoice_id)
            response = self.stub.DeleteInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            return response.success
        except grpc.RpcError as e:
            print(f"❌ Error: {e.details()}")
            return False
    
    def initiate_payment(self, invoice_id: str, amount: float, payment_method: str = "transfer"):
        """Initiate a payment for an invoice"""
        print(f"\n Initiating payment for invoice: {invoice_id}")
        try:
            request = PB2.PaymentRequest(
                invoice_id=invoice_id,
                amount=amount,
                payment_method=payment_method
            )
            response = self.stub.InitiatePayment(request, timeout=5)
            print(f"✅ Success: {response.message}")
            print(f"   Payment ID: {response.payment_id}")
            return response
        except grpc.RpcError as e:
            print(f"❌ Error: {e.details()}")
            return None
    
    def close(self):
        """Close the connection"""
        self.channel.close()


def main():
    """Main test scenario"""
    print("=" * 60)
    print(" Invoice Service gRPC Client - Test Scenario")
    print("=" * 60)
    
    # Connect to gRPC server
    client = InvoiceClient(host='localhost', port=50051)
    
    try:
        # Create invoices
        client.create_invoice("INV-001", "Acme Corp", 1250.00)
        client.create_invoice("INV-002", "TechCorp GmbH", 3500.50)
        client.create_invoice("INV-003", "DataSolutions Ltd", 890.00)
        
        # List invoices
        time.sleep(1)
        client.list_invoices()
        
        # Get specific invoice
        time.sleep(1)
        client.get_invoice("INV-001")
        
        # Update invoice
        time.sleep(1)
        client.update_invoice("INV-002", "TechCorp GmbH", 3600.00)
        
        # Initiate payment
        time.sleep(1)
        client.initiate_payment("INV-001", 1250.00, "transfer")
        
        # Wait for payment to be processed
        print("\n Waiting for payment processing...")
        time.sleep(3)
        
        # Check invoice status after payment
        time.sleep(1)
        client.get_invoice("INV-001")
        
        # List all invoices again
        time.sleep(1)
        client.list_invoices()
        
        # Delete an invoice
        time.sleep(1)
        client.delete_invoice("INV-003")
        
        # Final list
        time.sleep(1)
        client.list_invoices()
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    finally:
        client.close()


if __name__ == '__main__':
    main()
