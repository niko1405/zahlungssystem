"""gRPC Server for Invoice Management Service.

This module implements CRUD operations for invoices and payment initiation.
It uses helper modules for database and RabbitMQ interactions and follows
lazy logging patterns for better runtime performance.
"""

# pyright: reportAttributeAccessIssue=false

import json
import uuid
from concurrent import futures
from datetime import datetime
from typing import Any

import grpc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import invoice_pb2
import invoice_pb2_grpc
from app.config.database import SessionLocal, engine
from app.models import Base
from app.utils import (
    StructuredLogger,
    RabbitMQConnection,
    create_invoice,
    delete_invoice,
    get_invoice_or_none,
    list_invoices,
    update_invoice,
)

logger = StructuredLogger.for_module(__name__)
PB2: Any = invoice_pb2

Base.metadata.create_all(bind=engine)


class InvoiceServiceServicer(invoice_pb2_grpc.InvoiceServiceServicer):
    """gRPC service implementation for invoice operations."""

    def __init__(self):
        """Initialize service dependencies.

        Creates one database session and one RabbitMQ connection manager for the
        servicer lifecycle.
        """
        self.db: Session = SessionLocal()
        self.rmq = RabbitMQConnection()
        self._setup_rabbitmq()

    def _setup_rabbitmq(self) -> None:
        """Initialize RabbitMQ connection and required queues.

        Raises:
            RuntimeError: If channel operations are attempted without a connection.
            pika.exceptions.AMQPError: If RabbitMQ connection retries are exhausted.
        """
        self.rmq.connect(max_retries=5, retry_delay=2)
        self.rmq.declare_queue("payment_orders", durable=True)
        self.rmq.declare_queue("payment_results", durable=True)
        logger.log_rabbitmq_event("CONNECTED", status="SUCCESS")

    @staticmethod
    def _to_proto(db_invoice) -> Any:
        """Map SQLAlchemy invoice model to protobuf message.

        Args:
            db_invoice: SQLAlchemy invoice entity.

        Returns:
            Protobuf invoice message representation.
        """
        return getattr(PB2, "Invoice")(  # pyright: ignore[reportAttributeAccessIssue]
            id=db_invoice.id,
            supplier=db_invoice.supplier,
            amount=db_invoice.amount,
            created_at=db_invoice.created_at.isoformat() if db_invoice.created_at else "",
            updated_at=db_invoice.updated_at.isoformat() if db_invoice.updated_at else "",
            status=db_invoice.status,
        )

    def CreateInvoice(self, request, context):
        """Create a new invoice.

        Args:
            request: CreateInvoiceRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing creation result and invoice payload.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For database-level failures.
            ValueError: For invalid data conversion scenarios.
            TypeError: For invalid request payload types.
        """
        logger.log_grpc_call("CreateInvoice", status="IN_PROGRESS", invoice_id=request.id)
        try:
            invoice = create_invoice(self.db, request.id, request.supplier, request.amount)
            if not invoice:
                context.abort(grpc.StatusCode.ALREADY_EXISTS, "Invoice already exists")

            logger.log_grpc_call("CreateInvoice", status="SUCCESS", invoice_id=request.id)
            return getattr(PB2, "InvoiceResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                success=True,
                message="Invoice created successfully",
                invoice=self._to_proto(invoice),
            )
        except (SQLAlchemyError, ValueError, TypeError) as exc:
            logger.log_error("CreateInvoice failed", exc_info=exc, invoice_id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error creating invoice")

    def GetInvoice(self, request, context):
        """Get one invoice by its identifier.

        Args:
            request: GetInvoiceRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing read result and invoice payload.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For database query failures.
        """
        logger.log_grpc_call("GetInvoice", status="IN_PROGRESS", invoice_id=request.id)
        try:
            invoice = get_invoice_or_none(self.db, request.id)
            if not invoice:
                context.abort(grpc.StatusCode.NOT_FOUND, "Invoice not found")

            logger.log_grpc_call("GetInvoice", status="SUCCESS", invoice_id=request.id)
            return getattr(PB2, "InvoiceResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                success=True,
                message="Invoice retrieved successfully",
                invoice=self._to_proto(invoice),
            )
        except SQLAlchemyError as exc:
            logger.log_error("GetInvoice failed", exc_info=exc, invoice_id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error retrieving invoice")

    def ListInvoices(self, request, context):
        """List invoices using offset pagination.

        Args:
            request: ListInvoicesRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing paged invoices and total count.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For database query/count failures.
        """
        skip = max(request.skip, 0)
        limit = request.limit if request.limit > 0 else 100
        logger.log_grpc_call("ListInvoices", status="IN_PROGRESS", skip=skip, limit=limit)
        try:
            invoices, total = list_invoices(self.db, skip=skip, limit=limit)
            logger.log_grpc_call("ListInvoices", status="SUCCESS", returned=len(invoices), total=total)
            return getattr(PB2, "ListInvoicesResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                invoices=[self._to_proto(invoice) for invoice in invoices],
                total=total,
            )
        except SQLAlchemyError as exc:
            logger.log_error("ListInvoices failed", exc_info=exc, skip=skip, limit=limit)
            context.abort(grpc.StatusCode.INTERNAL, "Error listing invoices")

    def UpdateInvoice(self, request, context):
        """Update supplier and/or amount for one invoice.

        Args:
            request: UpdateInvoiceRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing update result and updated invoice.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For database update failures.
            ValueError: For invalid value conversion scenarios.
            TypeError: For invalid request payload types.
        """
        logger.log_grpc_call("UpdateInvoice", status="IN_PROGRESS", invoice_id=request.id)
        try:
            updated = update_invoice(
                self.db,
                request.id,
                supplier=request.supplier if request.supplier else None,
                amount=request.amount if request.amount else None,
            )
            if not updated:
                context.abort(grpc.StatusCode.NOT_FOUND, "Invoice not found")

            logger.log_grpc_call("UpdateInvoice", status="SUCCESS", invoice_id=request.id)
            return getattr(PB2, "InvoiceResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                success=True,
                message="Invoice updated successfully",
                invoice=self._to_proto(updated),
            )
        except (SQLAlchemyError, ValueError, TypeError) as exc:
            logger.log_error("UpdateInvoice failed", exc_info=exc, invoice_id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error updating invoice")

    def DeleteInvoice(self, request, context):
        """Delete one invoice by identifier.

        Args:
            request: DeleteInvoiceRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing delete status payload.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For database delete failures.
        """
        logger.log_grpc_call("DeleteInvoice", status="IN_PROGRESS", invoice_id=request.id)
        try:
            success = delete_invoice(self.db, request.id)
            if not success:
                context.abort(grpc.StatusCode.NOT_FOUND, "Invoice not found")

            logger.log_grpc_call("DeleteInvoice", status="SUCCESS", invoice_id=request.id)
            return getattr(PB2, "DeleteInvoiceResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                success=True,
                message="Invoice deleted successfully",
            )
        except SQLAlchemyError as exc:
            logger.log_error("DeleteInvoice failed", exc_info=exc, invoice_id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error deleting invoice")

    def InitiatePayment(self, request, context):
        """Initiate asynchronous payment processing for an invoice.

        Args:
            request: PaymentRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing payment order details.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For invoice lookup failures.
            RuntimeError: If RabbitMQ is not connected.
            ValueError: For invalid JSON serialization values.
            TypeError: For non-serializable payload values.
        """
        logger.log_grpc_call(
            "InitiatePayment",
            status="IN_PROGRESS",
            invoice_id=request.invoice_id,
            amount=request.amount,
        )
        try:
            invoice = get_invoice_or_none(self.db, request.invoice_id)
            if not invoice:
                context.abort(grpc.StatusCode.NOT_FOUND, "Invoice not found")

            payment_id = str(uuid.uuid4())
            payload = {
                "id": payment_id,
                "invoice_id": request.invoice_id,
                "amount": request.amount,
                "payment_method": request.payment_method,
                "timestamp": int(datetime.now().timestamp()),
                "status": "pending",
            }
            self.rmq.publish_message("payment_orders", json.dumps(payload), persistent=True)

            logger.log_grpc_call("InitiatePayment", status="SUCCESS", payment_id=payment_id)
            return getattr(PB2, "PaymentResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                success=True,
                message="Payment order created",
                payment_id=payment_id,
            )
        except (SQLAlchemyError, RuntimeError, ValueError, TypeError) as exc:
            logger.log_error(
                "InitiatePayment failed",
                exc_info=exc,
                invoice_id=request.invoice_id,
            )
            context.abort(grpc.StatusCode.INTERNAL, "Error initiating payment")


def serve() -> None:
    """Start and run the gRPC server.

    Raises:
        RuntimeError: If gRPC server initialization fails.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    invoice_pb2_grpc.add_InvoiceServiceServicer_to_server(InvoiceServiceServicer(), server)
    server.add_insecure_port("[::]:50051")

    logger.log_grpc_call("GRPCServer", status="STARTING")
    server.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.log_grpc_call("GRPCServer", status="STOPPING")
        server.stop(grace=0)


if __name__ == "__main__":
    serve()
