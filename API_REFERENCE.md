# Helper Modules API Reference

## Table of Contents
1. [Logging Config](#logging-config)
2. [Database Helpers](#database-helpers)
3. [RabbitMQ Helpers](#rabbitmq-helpers)
4. [Integration Examples](#integration-examples)

---

## Logging Config

Module: `app.utils.logging_config`

### setup_logging(name, level="INFO", log_format=None)

Initialize a logger with lazy evaluation patterns.

**Parameters:**
- `name` (str): Logger name, typically `__name__`
- `level` (str): Logging level - "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- `log_format` (str, optional): Custom format string

**Returns:** `logging.Logger` instance

**Example:**
```python
from app.utils import setup_logging

logger = setup_logging(__name__, level="DEBUG")
logger.info("Starting application")
logger.debug("Debug info: %s", debug_data)
```

---

### get_logger(name, level="INFO")

Convenience function to get or create a logger.

**Parameters:**
- `name` (str): Logger name
- `level` (str): Logging level

**Returns:** `logging.Logger` instance

**Example:**
```python
from app.utils import get_logger

logger = get_logger("myapp.service")
```

---

### StructuredLogger Class

Wrapper for semantic logging with lazy evaluation.

#### Creation

```python
from app.utils import StructuredLogger

# Method 1: From existing logger
logger = StructuredLogger(base_logger)

# Method 2: For a module (recommended)
logger = StructuredLogger.for_module(__name__, level="INFO")
```

#### Methods

##### log_grpc_call(method_name, status="IN_PROGRESS", **context_data)

Log a gRPC method call.

**Parameters:**
- `method_name` (str): gRPC method name
- `status` (str): Status - "IN_PROGRESS", "SUCCESS", "FAILED"
- `**context_data`: Additional context (lazy evaluated)

**Example:**
```python
logger.log_grpc_call("CreateInvoice", status="IN_PROGRESS")
logger.log_grpc_call("CreateInvoice", status="SUCCESS", invoice_id="INV-001", amount=99.99)
logger.log_grpc_call("CreateInvoice", status="FAILED", error_code="INVALID_INPUT")
```

---

##### log_db_operation(operation, entity, status="SUCCESS", **details)

Log a database operation.

**Parameters:**
- `operation` (str): Operation type - "CREATE", "READ", "UPDATE", "DELETE"
- `entity` (str): Entity type being operated on (e.g., "invoice", "payment")
- `status` (str): Operation status - "SUCCESS", "FAILED", "SKIPPED"
- `**details`: Additional details about the operation

**Example:**
```python
logger.log_db_operation("CREATE", "invoice", status="SUCCESS", invoice_id="INV-001", supplier="Acme")
logger.log_db_operation("UPDATE", "invoice", status="SUCCESS", invoice_id="INV-001", old_status="pending", new_status="paid")
logger.log_db_operation("DELETE", "invoice", status="SUCCESS", invoice_id="INV-001")
```

---

##### log_rabbitmq_event(event, status="SUCCESS", **context)

Log a RabbitMQ event.

**Parameters:**
- `event` (str): Event type - "CONNECTED", "MESSAGE_RECEIVED", "MESSAGE_SENT", "ERROR"
- `status` (str): Status - "SUCCESS", "FAILED", "IN_PROGRESS"
- `**context`: Event context (lazy evaluated)

**Example:**
```python
logger.log_rabbitmq_event("CONNECTED", status="SUCCESS")
logger.log_rabbitmq_event("MESSAGE_RECEIVED", status="SUCCESS", queue="payment_orders", message_id="MSG-123")
logger.log_rabbitmq_event("MESSAGE_SENT", status="SUCCESS", queue="payment_results")
logger.log_rabbitmq_event("DISCONNECTED", status="SUCCESS")
```

---

##### log_error(message, exc_info=None, **context)

Log an error with optional exception information.

**Parameters:**
- `message` (str): Error message
- `exc_info` (Exception, optional): Exception object to include stacktrace
- `**context`: Additional error context

**Example:**
```python
try:
    risky_operation()
except (RuntimeError, ValueError) as e:
    logger.log_error("Operation failed", exc_info=e, invoice_id="INV-001")

# Or without exception
logger.log_error("Payment declined", payment_id="PAY-123", reason="Insufficient funds")
```

---

##### log_warning(message, **context)

Log a warning message.

**Parameters:**
- `message` (str): Warning message
- `**context`: Additional context

**Example:**
```python
logger.log_warning("Slow database query", duration_ms=2500, query="SELECT *")
logger.log_warning("Invoice already exists", invoice_id="INV-001")
```

---

##### log_debug(message, **context)

Log debug information (only shown when DEBUG level enabled).

**Parameters:**
- `message` (str): Debug message
- `**context**: Additional context

**Example:**
```python
logger.log_debug("Processing order", order_id="ORD-123")
logger.log_debug("Cache hit", cache_key="user:42", ttl=3600)
```

---

## Database Helpers

Module: `app.utils.db_helpers`

All functions accept a SQLAlchemy `Session` object as first parameter.

### get_invoice_or_none(db, invoice_id)

Retrieve an invoice by ID.

**Parameters:**
- `db` (Session): Database session
- `invoice_id` (str): Invoice ID

**Returns:** Invoice model or None

**Raises:** `sqlalchemy.exc.SQLAlchemyError` when the database query fails

**Example:**
```python
from app.config.database import SessionLocal
from app.utils import get_invoice_or_none

db = SessionLocal()
invoice = get_invoice_or_none(db, "INV-001")

if invoice:
    print(f"Found: {invoice.supplier} - {invoice.amount}€")
else:
    print("Invoice not found")
```

---

### create_invoice(db, invoice_id, supplier, amount)

Create a new invoice.

**Parameters:**
- `db` (Session): Database session
- `invoice_id` (str): Unique invoice ID
- `supplier` (str): Supplier name
- `amount` (float): Invoice amount

**Returns:** Created Invoice or None if already exists

**Raises:** `sqlalchemy.exc.SQLAlchemyError` when the create transaction fails

**Example:**
```python
from app.utils import create_invoice

invoice = create_invoice(db, "INV-001", "Acme Corp", 1500.00)

if invoice:
    print("✓ Invoice created")
else:
    print("✗ Invoice already exists")
```

---

### update_invoice(db, invoice_id, supplier=None, amount=None)

Update an invoice's supplier and/or amount.

**Parameters:**
- `db` (Session): Database session
- `invoice_id` (str): Invoice ID to update
- `supplier` (str, optional): New supplier name
- `amount` (float, optional): New amount

**Returns:** Updated Invoice or None if not found

**Example:**
```python
from app.utils import update_invoice

# Update both fields
invoice = update_invoice(db, "INV-001", supplier="Acme Inc", amount=2000.00)

# Update only supplier
invoice = update_invoice(db, "INV-001", supplier="New Supplier")

# Update only amount
invoice = update_invoice(db, "INV-001", amount=3000.00)
```

---

### update_invoice_status(db, invoice_id, new_status)

Update only the invoice status.

**Parameters:**
- `db` (Session): Database session
- `invoice_id` (str): Invoice ID
- `new_status` (str): New status ("pending", "paid", "cancelled")

**Returns:** Updated Invoice or None if not found

**Example:**
```python
from app.utils import update_invoice_status

# Mark as paid
invoice = update_invoice_status(db, "INV-001", "paid")

if invoice and invoice.status == "paid":
    print("✓ Invoice marked as paid")
```

---

### delete_invoice(db, invoice_id)

Delete an invoice.

**Parameters:**
- `db` (Session): Database session
- `invoice_id` (str): Invoice ID to delete

**Returns:** True if deleted, False if not found

**Example:**
```python
from app.utils import delete_invoice

deleted = delete_invoice(db, "INV-001")

if deleted:
    print("✓ Invoice deleted")
else:
    print("✗ Invoice not found")
```

---

### list_invoices(db, skip=0, limit=100)

List invoices with pagination.

**Parameters:**
- `db` (Session): Database session
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 100)

**Returns:** Tuple of (invoices_list, total_count)

**Example:**
```python
from app.utils import list_invoices

invoices, total = list_invoices(db, skip=0, limit=10)

print(f"Got {len(invoices)} of {total} total invoices")

for invoice in invoices:
    print(f"- {invoice.id}: {invoice.supplier} ({invoice.status})")
```

---

## RabbitMQ Helpers

Module: `app.utils.rabbitmq_helpers`

### RabbitMQConnection Class

Manage RabbitMQ connections with retry logic and queue operations.

#### Initialization

```python
from app.utils import RabbitMQConnection

# Create connection manager
rmq = RabbitMQConnection(rabbitmq_url=None)

# URL defaults to RABBITMQ_URL environment variable
# or "amqp://guest:guest@rabbitmq:5672/"
```

#### connect(max_retries=5, retry_delay=2)

Establish connection to RabbitMQ with retries.

**Parameters:**
- `max_retries` (int): Maximum connection attempts
- `retry_delay` (int): Delay between retries (seconds)

**Raises:** `pika.exceptions.AMQPConnectionError` if all retries fail

**Example:**
```python
from app.utils import RabbitMQConnection

rmq = RabbitMQConnection()

try:
    rmq.connect(max_retries=5, retry_delay=2)
    print("✓ Connected to RabbitMQ")
except pika.exceptions.AMQPError as e:
    print(f"✗ Failed to connect: {e}")
```

---

#### declare_queue(queue_name, durable=True)

Declare a queue on RabbitMQ.

**Parameters:**
- `queue_name` (str): Queue name
- `durable` (bool): Whether queue survives broker restarts

**Example:**
```python
rmq.declare_queue('payment_orders', durable=True)
rmq.declare_queue('payment_results', durable=True)
```

---

#### publish_message(queue_name, message_body, persistent=True)

Publish a message to a queue.

**Parameters:**
- `queue_name` (str): Target queue name
- `message_body` (str): Message content (usually JSON)
- `persistent` (bool): Whether message survives broker restarts

**Example:**
```python
import json

payment_order = {
    "id": "PAY-123",
    "invoice_id": "INV-001",
    "amount": 500.00,
    "timestamp": int(time.time())
}

rmq.publish_message(
    'payment_orders',
    json.dumps(payment_order),
    persistent=True
)
```

---

#### setup_consumer(queue_name, callback, prefetch_count=1)

Setup a message consumer.

**Parameters:**
- `queue_name` (str): Queue to consume from
- `callback` (callable): Function called for each message: `callback(ch, method, properties, body)`
- `prefetch_count` (int): Max messages to process simultaneously

**Example:**
```python
def process_message(ch, method, properties, body):
    try:
        message = json.loads(body.decode('utf-8'))
        print(f"Processing: {message}")
        
        # Process message...
        
        ch.basic_ack(delivery_tag=method.delivery_tag)  # Mark as processed
    except (json.JSONDecodeError, RuntimeError) as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # Retry

rmq.setup_consumer('payment_orders', process_message, prefetch_count=1)
```

---

#### start_consuming()

Start consuming messages (blocking).

**Example:**
```python
print("Waiting for messages...")
rmq.start_consuming()  # Blocks until interrupted
```

---

#### stop_consuming()

Stop consuming and close connection.

**Example:**
```python
try:
    rmq.start_consuming()
except KeyboardInterrupt:
    rmq.stop_consuming()
    print("Disconnected")
```

---

#### Context Manager Usage

```python
from app.utils import RabbitMQConnection

with RabbitMQConnection() as rmq:
    rmq.connect()
    rmq.declare_queue('my_queue', durable=True)
    
    # Connection automatically closes after block
```

---

## Integration Examples

### Example 1: Complete Payment Service

```python
from app.utils import (
    StructuredLogger,
    RabbitMQConnection,
    get_invoice_or_none,
    update_invoice_status
)
from app.config.database import SessionLocal
import json

logger = StructuredLogger.for_module(__name__)

class PaymentService:
    def __init__(self):
        self.db = SessionLocal()
        self.rmq = RabbitMQConnection()
        self.rmq.connect()
        self.rmq.declare_queue('payment_orders', durable=True)
        self.rmq.setup_consumer('payment_orders', self.process)
    
    def process(self, ch, method, properties, body):
        try:
            payment = json.loads(body.decode('utf-8'))
            
            logger.log_rabbitmq_event("PAYMENT_RECEIVED", 
                                      status="IN_PROGRESS",
                                      payment_id=payment['id'])
            
            # Validate invoice
            invoice = get_invoice_or_none(self.db, payment['invoice_id'])
            if not invoice:
                logger.log_warning("Invoice not found", 
                                 invoice_id=payment['invoice_id'])
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Process payment
            logger.log_db_operation("UPDATE", "invoice", 
                                  status="IN_PROGRESS",
                                  invoice_id=invoice.id)
            
            updated = update_invoice_status(self.db, invoice.id, "paid")
            
            if updated:
                logger.log_db_operation("UPDATE", "invoice", 
                                      status="SUCCESS",
                                      invoice_id=invoice.id,
                                      new_status="paid")
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except (json.JSONDecodeError, RuntimeError, KeyError) as e:
            logger.log_error("Payment processing failed", 
                           exc_info=e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start(self):
        try:
            self.rmq.start_consuming()
        except KeyboardInterrupt:
            self.rmq.stop_consuming()

if __name__ == '__main__':
    service = PaymentService()
    service.start()
```

---

### Example 2: Complete gRPC Service

```python
import grpc
from app.utils import (
    StructuredLogger,
    RabbitMQConnection,
    create_invoice,
    get_invoice_or_none,
    list_invoices
)
from app.config.database import SessionLocal

logger = StructuredLogger.for_module(__name__)

class InvoiceService:
    def __init__(self):
        self.db = SessionLocal()
        self.rmq = RabbitMQConnection()
        self.rmq.connect()
        self.rmq.declare_queue('payment_orders', durable=True)
    
    def CreateInvoice(self, request, context):
        logger.log_grpc_call("CreateInvoice", 
                           status="IN_PROGRESS",
                           invoice_id=request.id)
        
        try:
            invoice = create_invoice(
                self.db,
                request.id,
                request.supplier,
                request.amount
            )
            
            if not invoice:
                context.abort(grpc.StatusCode.ALREADY_EXISTS, 
                            "Invoice already exists")
            
            logger.log_grpc_call("CreateInvoice", 
                               status="SUCCESS",
                               invoice_id=invoice.id)
            
            return InvoiceResponse(success=True, invoice=convert(invoice))
            
        except (RuntimeError, TypeError) as e:
            logger.log_error("CreateInvoice failed", 
                           exc_info=e,
                           invoice_id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error creating invoice")
    
    def ListInvoices(self, request, context):
        logger.log_grpc_call("ListInvoices", 
                           status="IN_PROGRESS")
        
        try:
            invoices, total = list_invoices(
                self.db,
                skip=request.skip,
                limit=request.limit
            )
            
            logger.log_grpc_call("ListInvoices", 
                               status="SUCCESS",
                               returned_count=len(invoices),
                               total=total)
            
            return ListInvoicesResponse(
                invoices=[convert(inv) for inv in invoices],
                total=total
            )
            
        except SQLAlchemyError as e:
            logger.log_error("ListInvoices failed", exc_info=e)
            context.abort(grpc.StatusCode.INTERNAL, "Error listing invoices")
```

---

## Error Handling Patterns

### Pattern 1: Graceful Degradation

```python
try:
    invoice = get_invoice_or_none(db, invoice_id)
    if not invoice:
        logger.log_warning("Invoice not found", invoice_id=invoice_id)
        return None
    return invoice
except SQLAlchemyError as e:
    logger.log_error("Database error", exc_info=e, invoice_id=invoice_id)
    return None
```

### Pattern 2: Retry Logic

```python
from time import sleep

for attempt in range(max_retries):
    try:
        rmq.connect(max_retries=1, retry_delay=0)
        break
    except pika.exceptions.AMQPError as e:
        logger.log_warning("Connection attempt failed", 
                         attempt=attempt+1,
                         max_retries=max_retries)
        if attempt < max_retries - 1:
            sleep(retry_delay)
```

### Pattern 3: Cascading Operations

```python
def process_payment(payment_order):
    # Step 1
    invoice = get_invoice_or_none(db, payment_order['invoice_id'])
    if not invoice:
        logger.log_warning("Step 1 failed: invoice not found")
        return False
    
    # Step 2
    if not validate(payment_order):
        logger.log_warning("Step 2 failed: validation error")
        return False
    
    # Step 3
    if not process(payment_order):
        logger.log_error("Step 3 failed: processing error")
        return False
    
    # Step 4
    updated = update_invoice_status(db, invoice.id, "paid")
    if not updated:
        logger.log_error("Step 4 failed: status update failed")
        return False
    
    logger.log_grpc_call("ProcessPayment", status="SUCCESS")
    return True
```

---

## Summary

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| logging_config | Lazy logging | `StructuredLogger`, `setup_logging()` |
| db_helpers | Database CRUD | `create_invoice()`, `update_invoice_status()`, `list_invoices()` |
| rabbitmq_helpers | Message queue | `RabbitMQConnection`, `publish_message()`, `setup_consumer()` |

All modules use **lazy evaluation** for performance and provide **semantic logging** for clarity.
