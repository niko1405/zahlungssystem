#!/usr/bin/env python3
"""
Test Client for Invoice Service
Demonstrates how to use the gRPC Invoice Service
"""

import sys
import time
import json
import os
import uuid
from typing import Any, cast
from types import SimpleNamespace
from datetime import datetime
import grpc
import pika

# Make sure generated stubs are importable when run as script or in Docker.
# Add parent directory to path for new structure
sys.path.insert(0, "..")
sys.path.insert(0, "/app")

from grpc_service.generated import invoice_pb2
from grpc_service.generated import invoice_pb2_grpc
from utils import RabbitMQConnection

PB2 = cast(Any, invoice_pb2)


class InvoiceClient:
    """Client for the gRPC Invoice Service"""
    
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = invoice_pb2_grpc.InvoiceServiceStub(self.channel)

    @staticmethod
    def _rpc_error_message(error: grpc.RpcError) -> str:
        """Extract a stable error message from grpc.RpcError."""
        details_fn = getattr(error, "details", None)
        if callable(details_fn):
            return str(details_fn())
        return str(error)
    
    def create_invoice(self, invoice_id: str, supplier: str, amount: float):
        """Create a new invoice"""
        print(f"\n Creating invoice: {invoice_id}")
        try:
            request = getattr(PB2, "CreateInvoiceRequest")(
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
            print(f"❌ Error: {self._rpc_error_message(e)}")
            return None
    
    def get_invoice(self, invoice_id: str):
        """Get an invoice by ID"""
        print(f"\n Getting invoice: {invoice_id}")
        try:
            request = getattr(PB2, "GetInvoiceRequest")(id=invoice_id)
            response = self.stub.GetInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            print(f"   ID: {response.invoice.id}")
            print(f"   Supplier: {response.invoice.supplier}")
            print(f"   Amount: {response.invoice.amount}€")
            print(f"   Status: {response.invoice.status}")
            return response.invoice
        except grpc.RpcError as e:
            print(f"❌ Error: {self._rpc_error_message(e)}")
            return None
    
    def list_invoices(self, skip=0, limit=10):
        """List all invoices"""
        print(f"\n Listing invoices (skip={skip}, limit={limit})")
        try:
            request = getattr(PB2, "ListInvoicesRequest")(skip=skip, limit=limit)
            response = self.stub.ListInvoices(request, timeout=5)
            print(f"✅ Found {len(response.invoices)} invoices (total: {response.total})")
            for inv in response.invoices:
                print(f"   - {inv.id}: {inv.supplier} ({inv.amount}€) - {inv.status}")
            return response.invoices
        except grpc.RpcError as e:
            print(f"❌ Error: {self._rpc_error_message(e)}")
            return []
    
    def update_invoice(self, invoice_id: str, supplier: str, amount: float):
        """Update an invoice"""
        print(f"\n Updating invoice: {invoice_id}")
        try:
            request = getattr(PB2, "UpdateInvoiceRequest")(
                id=invoice_id,
                supplier=supplier,
                amount=amount
            )
            response = self.stub.UpdateInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            print(f"   New Amount: {response.invoice.amount}€")
            return response.invoice
        except grpc.RpcError as e:
            print(f"❌ Error: {self._rpc_error_message(e)}")
            return None
    
    def delete_invoice(self, invoice_id: str):
        """Delete an invoice"""
        print(f"\n Deleting invoice: {invoice_id}")
        try:
            request = getattr(PB2, "DeleteInvoiceRequest")(id=invoice_id)
            response = self.stub.DeleteInvoice(request, timeout=5)
            print(f"✅ Success: {response.message}")
            return response.success
        except grpc.RpcError as e:
            print(f"❌ Error: {self._rpc_error_message(e)}")
            return False
    
    def initiate_payment(self, invoice_id: str, amount: float, payment_method: str = "transfer"):
        """Create a payment order directly in RabbitMQ."""
        print(f"\n Initiating payment for invoice: {invoice_id}")
        rmq = RabbitMQConnection(
            rabbitmq_url=os.getenv(
                "RABBITMQ_URL",
                "amqp://guest:guest@localhost:5672/%2F?heartbeat=300&blocked_connection_timeout=300"
            )
        )
        try:
            # Keep pre-validation behavior by checking invoice existence via gRPC.
            invoice = self.get_invoice(invoice_id)
            if not invoice:
                print("❌ Error: Invoice not found")
                return None

            payment_id = str(uuid.uuid4())
            payload = {
                "id": payment_id,
                "invoice_id": invoice_id,
                "amount": amount,
                "payment_method": payment_method,
                "timestamp": int(datetime.now().timestamp()),
                "status": "pending",
                "requested_by": "client/test_client.py",
            }

            rmq.connect(max_retries=5, retry_delay=2)
            rmq.declare_queue("payment_orders", durable=True)
            rmq.publish_message("payment_orders", json.dumps(payload), persistent=True)

            response = SimpleNamespace(
                success=True,
                message="Payment order created",
                payment_id=payment_id,
            )

            print(f"✅ Success: {response.message}")
            print(f"   Payment ID: {response.payment_id}")
            return response
        except (pika.exceptions.AMQPError, RuntimeError, ValueError, TypeError) as e:
            print(f"❌ Error: {e}")
            return None
        finally:
            rmq.stop_consuming()
    
    def close(self):
        """Close the connection"""
        self.channel.close()


def main() -> int:
    """Main test scenario"""
    print("=" * 60)
    print(" Invoice Service gRPC Client - Test Scenario")
    print("=" * 60)
    
    # Connect to gRPC server
    client = InvoiceClient(host='localhost', port=50051)
    had_failures = False
    total_steps = 0
    passed_steps = 0

    def check_step(step_name: str, condition: bool) -> None:
        """Track failed test steps and print a concise marker."""
        nonlocal had_failures, total_steps, passed_steps
        total_steps += 1
        if condition:
            passed_steps += 1
            print(f"   [OK] {step_name}")
        else:
            had_failures = True
            print(f"   [FAILED] {step_name}")
    
    try:
        # Create invoices
        inv_1 = client.create_invoice("INV-001", "Acme Corp", 1250.00)
        inv_2 = client.create_invoice("INV-002", "TechCorp GmbH", 3500.50)
        inv_3 = client.create_invoice("INV-003", "DataSolutions Ltd", 890.00)
        check_step("Create INV-001", inv_1 is not None)
        check_step("Create INV-002", inv_2 is not None)
        check_step("Create INV-003", inv_3 is not None)
        
        # List invoices
        time.sleep(1)
        invoices = client.list_invoices()
        check_step("List invoices (initial)", len(invoices) > 0)
        
        # Get specific invoice
        time.sleep(1)
        invoice = client.get_invoice("INV-001")
        check_step("Get INV-001", invoice is not None)
        
        # Update invoice
        time.sleep(1)
        updated_invoice = client.update_invoice("INV-002", "TechCorp GmbH", 3600.00)
        check_step("Update INV-002", updated_invoice is not None)
        
        # Initiate payment
        time.sleep(1)
        payment_response = client.initiate_payment("INV-001", 1250.00, "transfer")
        check_step("Publish payment order for INV-001", payment_response is not None)
        
        # Wait for payment to be processed
        print("\n Waiting for payment processing...")
        time.sleep(3)
        
        # Check invoice status after payment
        time.sleep(1)
        paid_invoice = client.get_invoice("INV-001")
        check_step(
            "Invoice INV-001 status is paid",
            paid_invoice is not None and getattr(paid_invoice, "status", "") == "paid"
        )
        
        # List all invoices again
        time.sleep(1)
        invoices_after_payment = client.list_invoices()
        check_step("List invoices (after payment)", len(invoices_after_payment) > 0)
        
        # Delete an invoice
        time.sleep(1)
        deleted = client.delete_invoice("INV-003")
        check_step("Delete INV-003", deleted)
        
        # Final list
        time.sleep(1)
        final_invoices = client.list_invoices()
        check_step("List invoices (final)", len(final_invoices) > 0)
        
        print("\n" + "=" * 60)
        failed_steps = total_steps - passed_steps
        print(f"Steps passed: {passed_steps}/{total_steps}")
        print(f"Steps failed: {failed_steps}/{total_steps}")
        if had_failures:
            print("❌ Test failed: one or more test steps failed")
            print("=" * 60)
            return 1
        else:
            print("✅ Test completed successfully!")
            print("=" * 60)
            return 0
    except (grpc.RpcError, RuntimeError, ValueError, TypeError, pika.exceptions.AMQPError) as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    finally:
        client.close()


if __name__ == '__main__':
    sys.exit(main())
