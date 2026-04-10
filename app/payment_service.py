"""Payment Processing Service - Consumes payment orders from RabbitMQ

This service:
    - Connects to RabbitMQ and listens for payment_orders messages
    - Requests invoice status updates through the gRPC API upon successful payment processing
    - Publishes results to the payment_results queue
    - Uses lazy logging patterns for performance optimization
    - Implements retry logic for RabbitMQ connection failures
"""

# pyright: reportAttributeAccessIssue=false

import json
import os
import time
from datetime import datetime
from typing import Any, Optional, cast

import grpc
import pika
from app.generated import invoice_pb2, invoice_pb2_grpc

# Import utilities
from app.utils import (
    StructuredLogger,
    RabbitMQConnection,
)


# Setup logging
logger = StructuredLogger.for_module(__name__)
PB2 = cast(Any, invoice_pb2)


class PaymentService:
    """Service to process payment orders from RabbitMQ.
    
    Implements a message consumer pattern that:
        1. Connects to RabbitMQ and declares queues
        2. Consumes messages from payment_orders queue
        3. Validates invoices and processes payments
        4. Calls gRPC service to update invoice status
        5. Publishes results to payment_results queue
    """
    
    def __init__(self):
        """Initialize the payment service with gRPC and RabbitMQ connections.

        Raises:
            RuntimeError: If infrastructure setup fails.
            pika.exceptions.AMQPError: If RabbitMQ connection cannot be established.
        """
        self.rmq = RabbitMQConnection()
        self.grpc_target = os.getenv("GRPC_SERVER_TARGET", "grpc-server:50051")
        self.grpc_channel = grpc.insecure_channel(self.grpc_target)
        self.grpc_stub: Any = invoice_pb2_grpc.InvoiceServiceStub(self.grpc_channel)
        
        logger.log_debug("Initializing PaymentService")
        self._setup_infrastructure()
    
    def _setup_infrastructure(self) -> None:
        """Setup RabbitMQ connection and declare queues.
        
        This is separated for testability and clarity.
        
        Raises:
            RuntimeError: If RabbitMQ channel is unavailable during queue declaration.
            pika.exceptions.AMQPError: If connection retries are exhausted.
        """
        try:
            self.rmq.connect(max_retries=5, retry_delay=2)
            self.rmq.declare_queue('payment_orders', durable=True)
            self.rmq.declare_queue('payment_results', durable=True)
            
            logger.log_rabbitmq_event("SETUP_COMPLETE", status="SUCCESS")
            
        except (pika.exceptions.AMQPError, RuntimeError) as e:
            logger.log_error(
                "Failed to setup infrastructure",
                exc_info=e
            )
            raise

    def _grpc_get_invoice(self, invoice_id: str):
        """Fetch invoice through gRPC API.

        Args:
            invoice_id: Target invoice identifier.

        Returns:
            Invoice payload from gRPC response or None when not found/error.
        """
        try:
            response = self.grpc_stub.GetInvoice(
                getattr(PB2, "GetInvoiceRequest")(id=invoice_id),
                timeout=5,
            )
            return response.invoice
        except grpc.RpcError as e:
            logger.log_error("gRPC GetInvoice failed", exc_info=e, invoice_id=invoice_id)
            return None

    def _grpc_update_invoice_status(self, invoice_id: str, status: str) -> bool:
        """Update invoice status through gRPC API.

        Args:
            invoice_id: Target invoice identifier.
            status: New status value.

        Returns:
            bool: True on success, False otherwise.
        """
        try:
            getattr(self.grpc_stub, "UpdateInvoiceStatus")(
                getattr(PB2, "UpdateInvoiceStatusRequest")(id=invoice_id, status=status),
                timeout=5,
            )
            return True
        except grpc.RpcError as e:
            logger.log_error(
                "gRPC UpdateInvoiceStatus failed",
                exc_info=e,
                invoice_id=invoice_id,
                new_status=status,
            )
            return False
    
    def _process_payment_message(self, body: str) -> Optional[dict]:
        """Parse and validate a payment order message.
        
        Args:
            body: JSON-encoded payment order message
            
        Returns:
            Parsed payment order dict or None if invalid

        Raises:
            json.JSONDecodeError: Captured internally and transformed into None.
            TypeError: Captured internally and transformed into None for non-dict payloads.
        """
        try:
            payment_order = json.loads(body)
            if not isinstance(payment_order, dict):
                raise TypeError("Payment order must be a JSON object")
            
            # Validate required fields
            required_fields = ['id', 'invoice_id', 'amount']
            if not all(field in payment_order for field in required_fields):
                logger.log_warning(
                    "Invalid payment order - missing fields",
                    payment_id=payment_order.get('id', 'unknown')
                )
                return None
            
            logger.log_debug("Payment order parsed", payment_id=payment_order['id'])
            return payment_order
            
        except (json.JSONDecodeError, TypeError) as e:
            logger.log_error("Failed to parse payment order JSON", exc_info=e)
            return None
    
    def _validate_invoice(self, invoice_id: str) -> bool:
        """Validate that an invoice exists.
        
        Args:
            invoice_id: ID of invoice to check
            
        Returns:
            True if invoice exists, False otherwise
        """
        invoice = self._grpc_get_invoice(invoice_id)
        
        if not invoice:
            logger.log_warning("Invoice not found", invoice_id=invoice_id)
            return False
        
        logger.log_debug(
            "Invoice validated",
            invoice_id=invoice_id,
            status=invoice.status
        )
        return True
    
    def _simulate_payment_processing(self, payment_order: dict) -> bool:
        """Simulate payment processing.
        
        In a real system, this would integrate with a payment gateway.
        
        Args:
            payment_order: Payment order data
            
        Returns:
            True if processing successful, False otherwise

        Raises:
            KeyError: Captured internally if required payment keys are missing.
            TypeError: Captured internally for invalid payment payload types.
        """
        try:
            logger.log_debug(
                "Simulating payment processing",
                payment_id=payment_order['id'],
                amount=payment_order['amount']
            )
            
            # Simulate processing time
            time.sleep(1)
            
            # In a real system, check payment gateway response
            return True
            
        except (KeyError, TypeError) as e:
            logger.log_error(
                "Payment processing simulation failed",
                exc_info=e,
                payment_id=payment_order.get('id', 'unknown')
            )
            return False
    
    def _update_invoice_status(self, invoice_id: str) -> bool:
        """Update invoice status to "paid" through gRPC.
        
        Args:
            invoice_id: ID of invoice to update
            
        Returns:
            bool: True if status update succeeded, False otherwise.
        """
        success = self._grpc_update_invoice_status(invoice_id, "paid")
        if not success:
            logger.log_warning("Failed to update invoice status via gRPC", invoice_id=invoice_id)
            return False

        logger.log_grpc_call(
            "UpdateInvoiceStatus",
            status="SUCCESS",
            invoice_id=invoice_id,
            new_status="paid",
        )
        return True
    
    def _send_payment_result(self, payment_id: str, invoice_id: str, success: bool, message: str) -> None:
        """Send payment result to RabbitMQ.
        
        Args:
            payment_id: Payment order ID
            invoice_id: Invoice ID
            success: Whether payment was successful
            message: Result message

        Raises:
            RuntimeError: Captured internally if RabbitMQ channel is unavailable.
            TypeError: Captured internally for non-serializable payload values.
            ValueError: Captured internally for invalid serialization values.
        """
        try:
            result = {
                "payment_id": payment_id,
                "invoice_id": invoice_id,
                "success": success,
                "status": "completed" if success else "failed",
                "message": message,
                "processed_at": int(datetime.now().timestamp())
            }
            
            self.rmq.publish_message(
                'payment_results',
                json.dumps(result),
                persistent=True
            )
            
            logger.log_rabbitmq_event(
                "PAYMENT_RESULT_SENT",
                status="SUCCESS" if success else "FAILED",
                payment_id=payment_id
            )
            
        except (RuntimeError, TypeError, ValueError) as e:
            logger.log_error(
                "Failed to send payment result",
                exc_info=e,
                payment_id=payment_id
            )
    
    def process_payment_order(self, ch, method, _properties, body: bytes) -> None:
        """Process a payment order from the queue (RabbitMQ callback).
        
        This method is called by RabbitMQ for each message. It:
            1. Parses the message
            2. Validates the invoice
            3. Simulates payment processing
            4. Calls gRPC to update invoice status
            5. Sends result back via RabbitMQ
            6. Acknowledges the message
        
        Args:
            ch: RabbitMQ channel
            method: Method frame
            _properties: Message properties (unused)
            body: Message body (bytes)

        Raises:
            UnicodeDecodeError: Captured internally for invalid byte payloads.
            RuntimeError: Captured internally if ACK/NACK operations fail.
            KeyError: Captured internally for invalid payment payload keys.
        """
        try:
            # Parse payment order
            payment_order = self._process_payment_message(body.decode('utf-8'))
            
            if not payment_order:
                logger.log_warning("Skipping invalid payment order")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            logger.log_rabbitmq_event(
                "PAYMENT_ORDER_RECEIVED",
                status="IN_PROGRESS",
                payment_id=payment_order['id']
            )
            
            # Validate invoice exists
            if not self._validate_invoice(payment_order['invoice_id']):
                self._send_payment_result(
                    payment_order['id'],
                    payment_order['invoice_id'],
                    False,
                    "Invoice not found"
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Process payment
            if not self._simulate_payment_processing(payment_order):
                self._send_payment_result(
                    payment_order['id'],
                    payment_order['invoice_id'],
                    False,
                    "Payment processing failed"
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return
            
            # Update invoice through gRPC
            updated = self._update_invoice_status(payment_order['invoice_id'])

            if not updated:
                self._send_payment_result(
                    payment_order['id'],
                    payment_order['invoice_id'],
                    False,
                    "Invoice status update failed"
                )
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return
            
            # Send success result
            self._send_payment_result(
                payment_order['id'],
                payment_order['invoice_id'],
                True,
                "Payment processed successfully"
            )
            
            logger.log_rabbitmq_event(
                "PAYMENT_ORDER_PROCESSED",
                status="SUCCESS",
                payment_id=payment_order['id'],
                invoice_id=payment_order['invoice_id']
            )
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except (UnicodeDecodeError, RuntimeError, KeyError) as e:
            logger.log_error(
                "Unexpected error in payment processing",
                exc_info=e
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start(self) -> None:
        """Start consuming payment orders.
        
        Blocking call that runs until interrupted.

        Raises:
            RuntimeError: If consumer setup fails.
            pika.exceptions.AMQPError: If RabbitMQ consume loop fails.
        """
        try:
            self.rmq.setup_consumer(
                'payment_orders',
                self.process_payment_order,
                prefetch_count=1
            )
            
            logger.log_rabbitmq_event("START_CONSUMING", status="IN_PROGRESS")
            self.rmq.start_consuming()
            
        except KeyboardInterrupt:
            logger.log_rabbitmq_event("STOP_CONSUMING", status="SUCCESS")
            self.rmq.stop_consuming()
        except (RuntimeError, pika.exceptions.AMQPError) as e:
            logger.log_error(
                "Error in payment service",
                exc_info=e
            )
            raise
        finally:
            self.grpc_channel.close()


def main() -> None:
    """Main entry point for the payment service.

    Raises:
        RuntimeError: If service bootstrap fails.
        pika.exceptions.AMQPError: If RabbitMQ initialization fails.
        grpc.RpcError: If gRPC calls fail during service lifecycle.
    """
    try:
        logger.log_debug("Starting Payment Service")
        service = PaymentService()
        service.start()
    except (RuntimeError, pika.exceptions.AMQPError, grpc.RpcError) as e:
        logger.log_error(
            "Payment Service failed to start",
            exc_info=e
        )
        raise


if __name__ == '__main__':
    main()
