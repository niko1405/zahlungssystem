"""Utility modules for the invoice management system.

This package contains shared utilities for logging, database operations,
and other cross-cutting concerns.

Modules:
    logging_config: Centralized logging with lazy evaluation patterns
    db_helpers: Database operation helpers (CRUD operations)
    rabbitmq_helpers: RabbitMQ connection and messaging utilities
"""

from .logging_config import setup_logging, get_logger, StructuredLogger
from .db_helpers import (
    get_invoice_or_none,
    create_invoice,
    update_invoice,
    update_invoice_status,
    delete_invoice,
    list_invoices,
)
from .rabbitmq_helpers import RabbitMQConnection

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    "StructuredLogger",
    # Database
    "get_invoice_or_none",
    "create_invoice",
    "update_invoice",
    "update_invoice_status",
    "delete_invoice",
    "list_invoices",
    # RabbitMQ
    "RabbitMQConnection",
]
