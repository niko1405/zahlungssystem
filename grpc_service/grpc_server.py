"""gRPC Server for Invoice Management Service.

This module implements CRUD operations for invoices.
It uses helper modules for database interactions and follows
lazy logging patterns for better runtime performance.
"""

# pyright: reportAttributeAccessIssue=false

import os
import sys
from concurrent import futures
from typing import Any

import grpc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import SessionLocal, engine, Base
from grpc_service.models import Invoice
from utils import (
    StructuredLogger,
    create_invoice,
    delete_invoice,
    get_invoice_or_none,
    list_invoices,
    update_invoice,
    update_invoice_status,
)

from .generated import invoice_pb2, invoice_pb2_grpc

logger = StructuredLogger.for_module(__name__)
PB2: Any = invoice_pb2

# Ensure the invoice table exists before serving requests.
Base.metadata.create_all(bind=engine, tables=[Invoice.__table__])


class InvoiceServiceServicer(invoice_pb2_grpc.InvoiceServiceServicer):
    """gRPC service implementation for invoice operations."""

    def __init__(self):
        """Initialize service dependencies.

        Creates one database session for the servicer lifecycle.
        """
        self.db: Session = SessionLocal()

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

    def UpdateInvoiceStatus(self, request, context):
        """Update status for one invoice.

        Args:
            request: UpdateInvoiceStatusRequest protobuf message.
            context: gRPC ServicerContext.

        Returns:
            Protobuf response containing update result and updated invoice.

        Raises:
            grpc.RpcError: Forwarded when context.abort is called.
            SQLAlchemyError: For database update failures.
            ValueError: For invalid status values.
            TypeError: For invalid request payload types.
        """
        logger.log_grpc_call(
            "UpdateInvoiceStatus",
            status="IN_PROGRESS",
            invoice_id=request.id,
            new_status=request.status,
        )
        try:
            updated = update_invoice_status(self.db, request.id, request.status)
            if not updated:
                context.abort(grpc.StatusCode.NOT_FOUND, "Invoice not found")

            logger.log_grpc_call(
                "UpdateInvoiceStatus",
                status="SUCCESS",
                invoice_id=request.id,
                new_status=request.status,
            )
            return getattr(PB2, "InvoiceResponse")(  # pyright: ignore[reportAttributeAccessIssue]
                success=True,
                message="Invoice status updated successfully",
                invoice=self._to_proto(updated),
            )
        except (SQLAlchemyError, ValueError, TypeError) as exc:
            logger.log_error("UpdateInvoiceStatus failed", exc_info=exc, invoice_id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error updating invoice status")

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
