# Quick Reference Guide

**Copy-paste solutions for common tasks.**

---

## 1. Basic Logging

```python
from app.utils import StructuredLogger

logger = StructuredLogger.for_module(__name__)

# Log a gRPC call
logger.log_grpc_call("MyMethod", status="SUCCESS", user_id=123)

# Log a database operation
logger.log_db_operation("CREATE", "invoice", status="SUCCESS", invoice_id="INV-001")

# Log a RabbitMQ event
logger.log_rabbitmq_event("CONNECTED", status="SUCCESS")

# Log an error
logger.log_error("Operation failed", exc_info=e, operation_id="OP-123")

# Log a warning
logger.log_warning("Resource not found", resource_id=abc)

# Log debug info
logger.log_debug("Cache hit", key=cache_key)
```

---

## 2. Database Operations

```python
from app.utils import (
    create_invoice, get_invoice_or_none, 
    update_invoice, update_invoice_status, 
    delete_invoice, list_invoices
)
from app.config.database import SessionLocal

db = SessionLocal()

# Create
invoice = create_invoice(db, "INV-001", "Acme", 1000.0)

# Read
invoice = get_invoice_or_none(db, "INV-001")

# Update
invoice = update_invoice(db, "INV-001", supplier="NewName", amount=2000.0)

# Update status
invoice = update_invoice_status(db, "INV-001", "paid")

# Delete
deleted = delete_invoice(db, "INV-001")

# List
invoices, total = list_invoices(db, skip=0, limit=10)
```

---

## 3. RabbitMQ Operations

```python
from app.utils import RabbitMQConnection
import json

rmq = RabbitMQConnection()
rmq.connect()

# Declare queue
rmq.declare_queue('my_queue', durable=True)

# Publish message
rmq.publish_message('my_queue', json.dumps({"msg": "hello"}))

# Consume messages
def callback(ch, method, properties, body):
    data = json.loads(body.decode())
    print(f"Got: {data}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

rmq.setup_consumer('my_queue', callback, prefetch_count=1)
rmq.start_consuming()
```

---

## 4. Common Patterns

### Pattern: Validate → Process → Update

```python
logger.log_grpc_call("DoSomething", status="IN_PROGRESS", record_id=rec_id)

# Step 1: Validate
item = get_invoice_or_none(db, rec_id)
if not item:
    logger.log_warning("Item not found", record_id=rec_id)
    return error

# Step 2: Process
if not process(item):
    logger.log_error("Processing failed", record_id=rec_id)
    return error

# Step 3: Update
item = update_invoice_status(db, rec_id, "processed")
if not item:
    logger.log_error("Update failed", record_id=rec_id)
    return error

logger.log_grpc_call("DoSomething", status="SUCCESS")
return success
```

### Pattern: Error Handling

```python
try:
    result = risky_operation()
    logger.log_grpc_call("Operation", status="SUCCESS")
except ValueError as e:
    logger.log_warning("Invalid input", exc_info=e)
    return error_response
except (RuntimeError, TypeError) as e:
    logger.log_error("Unexpected error", exc_info=e)
    return error_response
```

### Pattern: RabbitMQ Message Processing

```python
def process_message(ch, method, properties, body):
    try:
        msg = json.loads(body.decode('utf-8'))
        logger.log_rabbitmq_event("MSG_RECEIVED", status="IN_PROGRESS", msg_id=msg['id'])
        
        # Do work
        if not do_work(msg):
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return
        
        logger.log_rabbitmq_event("MSG_PROCESSED", status="SUCCESS", msg_id=msg['id'])
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except (json.JSONDecodeError, RuntimeError, KeyError) as e:
        logger.log_error("Message processing failed", exc_info=e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
```

---

## 5. Integration Examples

### gRPC Server Method

```python
import grpc
from app.utils import StructuredLogger, create_invoice

logger = StructuredLogger.for_module(__name__)

class MyService(MyService_pb2_grpc.MyServiceServicer):
    def Create(self, request, context):
        logger.log_grpc_call("Create", status="IN_PROGRESS", id=request.id)
        
        try:
            item = create_invoice(db, request.id, request.name, request.value)
            
            if not item:
                context.abort(grpc.StatusCode.ALREADY_EXISTS, "Already exists")
            
            logger.log_grpc_call("Create", status="SUCCESS", id=item.id)
            return Response(success=True, item=convert(item))
            
        except (RuntimeError, TypeError) as e:
            logger.log_error("Create failed", exc_info=e, id=request.id)
            context.abort(grpc.StatusCode.INTERNAL, "Error")
```

### RabbitMQ Consumer Service

```python
from app.utils import RabbitMQConnection, update_invoice_status

class PaymentService:
    def __init__(self):
        self.rmq = RabbitMQConnection()
        self.rmq.connect()
        self.rmq.setup_consumer('payments', self.process)
    
    def process(self, ch, method, properties, body):
        try:
            payment = json.loads(body.decode())
            
            # Process payment
            if not validate(payment):
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            # Update database
            update_invoice_status(db, payment['invoice_id'], 'paid')
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except (json.JSONDecodeError, RuntimeError, KeyError) as e:
            logger.log_error("Payment processing failed", exc_info=e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start(self):
        try:
            self.rmq.start_consuming()
        except KeyboardInterrupt:
            self.rmq.stop_consuming()
```

---

## 6. Lazy Logging Cheat Sheet

```python
# ✅ GOOD - Lazy evaluation
logger.debug("User: %s", user_name)
logger.info("Amount: %s", expensive_calculation())
logger.warning("Large data: %s", big_dict)

# ❌ BAD - Eager evaluation
logger.debug(f"User: {user_name}")
logger.info(f"Amount: {expensive_calculation()}")
logger.warning(f"Large data: {big_dict}")
```

---

## 7. Status Strings to Use

### gRPC Calls
- `"IN_PROGRESS"` - Operation started
- `"SUCCESS"` - Operation completed successfully
- `"FAILED"` - Operation failed
- `"SKIPPED"` - Operation skipped (e.g., already exists)

### Database Operations
- `"IN_PROGRESS"` - Operation in progress
- `"SUCCESS"` - Operation successful
- `"FAILED"` - Operation failed
- `"SKIPPED"` - Operation skipped

### RabbitMQ Events
- `"IN_PROGRESS"` - Event processing
- `"SUCCESS"` - Event handled successfully
- `"FAILED"` - Event handling failed
- `"CONNECTED"` - Connection established
- `"DISCONNECTED"` - Connection closed
- `"MESSAGE_SENT"` - Message published
- `"MESSAGE_RECEIVED"` - Message received

---

## 8. Entity Types for DB Logging

- `"invoice"` - Invoice entity
- `"payment"` - Payment entity
- `"user"` - User entity
- `"order"` - Order entity
- `"invoice_status"` - Invoice status update

---

## 9. RabbitMQ Event Types

- `"CONNECTED"` - Connection successful
- `"DISCONNECTED"` - Connection closed
- `"MESSAGE_SENT"` - Message published
- `"MESSAGE_RECEIVED"` - Message consumed
- `"PAYMENT_ORDER_RECEIVED"` - Payment order arrived
- `"PAYMENT_ORDER_PROCESSED"` - Payment order finished
- `"START_CONSUMING"` - Consumer started
- `"STOP_CONSUMING"` - Consumer stopped

---

## 10. Common Context Fields

```python
# For invoices
invoice_id="INV-001"
supplier="Acme Corp"
amount=1000.0
status="pending"

# For payments
payment_id="PAY-123"
invoice_id="INV-001"
amount=500.0
payment_method="credit_card"

# For operations
operation="create_invoice"
duration_ms=250
rows_affected=1
error_code="INVALID_INPUT"

# For RabbitMQ
queue="payment_orders"
message_id="MSG-456"
size_bytes=256
```

---

## 11. Files Reference

| File | Purpose | Key Classes |
|------|---------|------------|
| `app/utils/logging_config.py` | Lazy logging | `StructuredLogger` |
| `app/utils/db_helpers.py` | Database ops | `create_invoice()`, `update_invoice_status()` |
| `app/utils/rabbitmq_helpers.py` | RabbitMQ ops | `RabbitMQConnection` |
| `app/utils/__init__.py` | Exports | All public functions |

---

## 12. Import Examples

```python
# Logging
from app.utils import StructuredLogger

# Database
from app.utils import (
    create_invoice,
    get_invoice_or_none,
    update_invoice,
    update_invoice_status,
    delete_invoice,
    list_invoices
)

# RabbitMQ
from app.utils import RabbitMQConnection

# Database Session
from app.config.database import SessionLocal
```

---

## 13. Environment Setup

```bash
# Set log level (if using custom setup)
export LOG_LEVEL=DEBUG

# RabbitMQ URL (if not running in docker-compose)
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Database URL (if using custom DB)
export DATABASE_URL=postgresql://user:pass@localhost/db
```

---

## 14. Quick Docker Commands

```bash
# View logs from gRPC server
docker compose logs -f grpc-server

# View logs from payment service
docker compose logs -f payment-service

# Check if services are running
docker compose ps

# Execute command in container
docker compose exec grpc-server python -c "from app.utils import StructuredLogger; print('✓ OK')"
```

---

## 15. Troubleshooting

**Q: Imports not found?**
```python
# Make sure to use absolute imports
from app.utils import StructuredLogger  # ✓
import app.utils                         # ✓
```

**Q: RabbitMQ connection failed?**
```python
# Check URL format
RABBITMQ_URL=amqp://user:pass@host:port/
# Example
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

**Q: Logs not showing?**
```python
# Set log level
logger = StructuredLogger.for_module(__name__, level="DEBUG")
```

**Q: Performance issues?**
```python
# Check for f-strings (eager evaluation)
logger.debug(f"Data: {big_object}")  # ✗ BAD
logger.debug("Data: %s", big_object)  # ✓ GOOD
```

**Q: Database connection failed?**
```python
# Check database URL in docker-compose.yml
# Default: postgresql://invoice_user:invoice_password@postgres:5432/invoice_db
```

---

## Quick Checklist

- [ ] Use `StructuredLogger.for_module(__name__)` for logging
- [ ] Use `%s` format specifiers, not f-strings
- [ ] Include relevant IDs/context in log calls
- [ ] Use helper functions from `db_helpers`
- [ ] Call `ch.basic_ack()` or `ch.basic_nack()` for RabbitMQ messages
- [ ] Wrap RabbitMQ callbacks in try/except
- [ ] Test with `docker compose` before deploying
- [ ] Check logs with `docker compose logs`

---

## Need More Help?

- **Logging Details**: See `LOGGING_GUIDE.md`
- **API Reference**: See `API_REFERENCE.md`
- **Refactoring Info**: See `REFACTORING_GUIDE.md`
- **Code Examples**: See inline docstrings in `app/utils/`
