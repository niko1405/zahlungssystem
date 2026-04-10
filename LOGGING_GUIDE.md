# Logging System Documentation

## Overview

The logging system uses **lazy evaluation patterns** to optimize performance by deferring string interpolation until necessary. This is particularly important for high-frequency logging or logging large objects.

## Core Concept: Lazy Logging

### The Problem with F-strings

```python
# ❌ PROBLEM: String is ALWAYS created, even if not logged
logger.debug(f"Processing user {expensive_function()}")  # Function called!
logger.debug(f"Large object: {large_dict}")              # Dict stringified!

# Even if DEBUG level is disabled, the function runs and strings are created
```

### The Solution: Format Specifiers

```python
# ✅ CORRECT: String only created if needed
logger.debug("Processing user %s", expensive_function())  # Only called if level enabled!
logger.debug("Large object: %s", large_dict)              # Only stringified if needed!

# If DEBUG is disabled: expensive_function() never runs, no string allocation
```

## Quick Start

### Basic Logging

```python
from app.utils import get_logger

logger = get_logger(__name__)

# These are lazy-evaluated
logger.info("User created: %s", user_id)
logger.warning("Warning: %s", critical_data)
logger.error("Error: %s", exc_info=e)
```

### Structured Logging

```python
from app.utils import StructuredLogger

logger = StructuredLogger.for_module(__name__)

# Semantic methods with lazy context
logger.log_grpc_call("ListInvoices", status="SUCCESS", count=42)
logger.log_db_operation("CREATE", "invoice", status="SUCCESS", invoice_id="INV-001")
logger.log_rabbitmq_event("CONNECTED", status="SUCCESS")
logger.log_error("Payment failed", exc_info=e, payment_id="PAY-123")
```

## Detailed Methods

### `StructuredLogger Methods`

#### `log_grpc_call(method_name, status, **context)`
Log gRPC method calls with contextual information.

```python
# Method call start
logger.log_grpc_call("CreateInvoice", status="IN_PROGRESS", invoice_id="INV-001")

# Method call success
logger.log_grpc_call("CreateInvoice", status="SUCCESS", invoice_id="INV-001", created_at="2024-01-10")

# Method call failure
logger.log_grpc_call("CreateInvoice", status="FAILED", invoice_id="INV-001", error_code="ALREADY_EXISTS")
```

**Output:**
```
gRPC CreateInvoice [IN_PROGRESS] - invoice_id=INV-001
gRPC CreateInvoice [SUCCESS] - invoice_id=INV-001, created_at=2024-01-10
gRPC CreateInvoice [FAILED] - invoice_id=INV-001, error_code=ALREADY_EXISTS
```

---

#### `log_db_operation(operation, entity, status, **details)`
Log database operations.

```python
# Create operation
logger.log_db_operation("CREATE", "invoice", status="SUCCESS", invoice_id="INV-001", supplier="Acme")

# Update operation
logger.log_db_operation("UPDATE", "invoice", status="SUCCESS", invoice_id="INV-001", old_status="pending", new_status="paid")

# Delete operation
logger.log_db_operation("DELETE", "invoice", status="SUCCESS", invoice_id="INV-001")
```

**Output:**
```
DB CREATE invoice [SUCCESS] - invoice_id=INV-001, supplier=Acme
DB UPDATE invoice [SUCCESS] - invoice_id=INV-001, old_status=pending, new_status=paid
DB DELETE invoice [SUCCESS] - invoice_id=INV-001
```

---

#### `log_rabbitmq_event(event, status, **context)`
Log RabbitMQ-related events.

```python
# Connection
logger.log_rabbitmq_event("CONNECTED", status="SUCCESS")

# Message received
logger.log_rabbitmq_event("MESSAGE_RECEIVED", status="SUCCESS", queue="payment_orders", message_id="MSG-123")

# Message sent
logger.log_rabbitmq_event("MESSAGE_SENT", status="SUCCESS", queue="payment_results", size_bytes=256)

# Error
logger.log_rabbitmq_event("CONNECTION_FAILED", status="FAILED", error="Connection timeout")
```

**Output:**
```
RabbitMQ CONNECTED [SUCCESS]
RabbitMQ MESSAGE_RECEIVED [SUCCESS] - queue=payment_orders, message_id=MSG-123
RabbitMQ MESSAGE_SENT [SUCCESS] - queue=payment_results, size_bytes=256
RabbitMQ CONNECTION_FAILED [FAILED] - error=Connection timeout
```

---

#### `log_error(message, exc_info, **context)`
Log errors with optional exception information.

```python
# Error with exception
try:
    risky_operation()
except (RuntimeError, ValueError) as e:
    logger.log_error("Operation failed", exc_info=e, operation="risky_operation", invoice_id="INV-001")

# Error without exception
logger.log_error("Payment declined", payment_id="PAY-123", reason="Insufficient funds")
```

**Output:**
```
Operation failed - operation=risky_operation, invoice_id=INV-001
Traceback (most recent call last):
  ...
```

---

#### `log_warning(message, **context)`
Log warnings with context.

```python
logger.log_warning("Slow operation", operation="list_invoices", duration_ms=2500, threshold_ms=1000)
logger.log_warning("Invoice already exists", invoice_id="INV-001")
```

**Output:**
```
Invoice already exists - invoice_id=INV-001
Slow operation - operation=list_invoices, duration_ms=2500, threshold_ms=1000
```

---

#### `log_debug(message, **context)`
Log debug information with context (only shown when DEBUG level enabled).

```python
logger.log_debug("Processing order", order_id="ORD-123", items=5)
logger.log_debug("Cache hit", cache_key="user:42", ttl_remaining=3600)
```

**Output (when DEBUG enabled):**
```
Processing order - order_id=ORD-123, items=5
Cache hit - cache_key=user:42, ttl_remaining=3600
```

---

## Usage Patterns

### Pattern 1: CRUD Operations

```python
from app.utils import StructuredLogger, create_invoice

logger = StructuredLogger.for_module(__name__)

# Create
logger.log_db_operation("CREATE", "invoice", status="IN_PROGRESS", invoice_id="INV-001")
invoice = create_invoice(db, "INV-001", "Acme", 1000.0)

if invoice:
    logger.log_db_operation("CREATE", "invoice", status="SUCCESS", invoice_id="INV-001")
else:
    logger.log_db_operation("CREATE", "invoice", status="SKIPPED", invoice_id="INV-001", reason="Already exists")
```

### Pattern 2: Error Handling

```python
def process_payment(payment_id, invoice_id):
    logger.log_grpc_call("InitiatePayment", status="IN_PROGRESS", payment_id=payment_id)
    
    try:
        invoice = get_invoice_or_none(db, invoice_id)
        
        if not invoice:
            logger.log_warning("Invoice not found", invoice_id=invoice_id)
            return False
        
        # Process payment...
        
        logger.log_grpc_call("InitiatePayment", status="SUCCESS", payment_id=payment_id)
        return True
        
    except (RuntimeError, TypeError) as e:
        logger.log_error(
            "Payment processing failed",
            exc_info=e,
            payment_id=payment_id,
            invoice_id=invoice_id
        )
        return False
```

### Pattern 3: Workflow Orchestration

```python
def handle_payment_order(payment_order):
    payment_id = payment_order['id']
    
    logger.log_rabbitmq_event(
        "PAYMENT_ORDER_RECEIVED",
        status="IN_PROGRESS",
        payment_id=payment_id
    )
    
    # Step 1: Validate
    if not validate(payment_order):
        logger.log_warning("Validation failed", payment_id=payment_id)
        return False
    
    # Step 2: Process
    if not process(payment_order):
        logger.log_warning("Processing failed", payment_id=payment_id)
        return False
    
    # Step 3: Persist
    if not persist(payment_order):
        logger.log_error("Persistence failed", payment_id=payment_id)
        return False
    
    logger.log_rabbitmq_event(
        "PAYMENT_ORDER_COMPLETED",
        status="SUCCESS",
        payment_id=payment_id
    )
    
    return True
```

---

## Log Levels

### DEBUG
- **When**: Development, troubleshooting
- **Amount**: High frequency, detailed
- **Example**: Cache hits, internal state, data conversions
- **Cost**: Minimal if disabled (lazy evaluation)

```python
logger.log_debug("Cache lookup", key=cache_key, ttl_remaining=seconds)
```

---

### INFO
- **When**: Normal operation, important milestones
- **Amount**: Regular, meaningful events
- **Example**: Request start/end, DB operations, state changes

```python
logger.log_grpc_call("CreateInvoice", status="SUCCESS", invoice_id=invoice_id)
```

---

### WARNING
- **When**: Potentially problematic but not critical
- **Amount**: Occasional, noteworthy
- **Example**: Missing resources, deprecated usage, performance issues

```python
logger.log_warning("Invoice not found", invoice_id=invoice_id)
```

---

### ERROR
- **When**: Something failed that needs attention
- **Amount**: Rare, needs investigation
- **Example**: Exceptions, validation failures, system errors

```python
logger.log_error("Payment failed", exc_info=e, payment_id=payment_id)
```

---

## Performance Impact

### Memory Savings Example

**Scenario:** Logging large object 1000 times per second

**F-string (eager):**
```python
large_dict = {"data": [1] * 1000000}  # 1MB

# This happens EVERY TIME, regardless of log level
logger.debug(f"Data: {large_dict}")  # 1MB allocated, 0.1s str conversion

# Per second: 1GB allocated, 100s spent converting
```

**Format specifier (lazy):**
```python
large_dict = {"data": [1] * 1000000}  # 1MB

# This happens ONLY if DEBUG enabled
logger.debug("Data: %s", large_dict)  # 0 allocation when disabled!

# Per second: 0 unless DEBUG enabled
```

**Savings:** 1GB/s memory allocation, 100s wasted conversion time

---

## Troubleshooting

### Issue: Logs not showing
**Solution:** Check log level
```python
logger = StructuredLogger.for_module(__name__, level="DEBUG")
```

### Issue: Performance degradation
**Solution:** Check for eager evaluation
```python
# Bad
logger.warning(f"Large data: {massive_object}")

# Good
logger.warning("Large data: %s", massive_object)
```

### Issue: Context not showing in output
**Solution:** Pass as keyword arguments
```python
# Bad
logger.log_grpc_call("Method", status="SUCCESS")

# Good
logger.log_grpc_call("Method", status="SUCCESS", invoice_id="INV-001", amount=100.0)
```

---

## Best Practices Summary

1. ✅ Use `%s` format specifiers
2. ✅ Use `StructuredLogger` methods for semantic context
3. ✅ Pass variables, not formatted strings
4. ✅ Include relevant IDs/identifiers in context
5. ✅ Log at appropriate levels
6. ✅ Include exception info for errors
7. ✅ Keep messages short and descriptive

---

## Examples Checklist

- [x] Basic logger creation
- [x] gRPC call logging
- [x] Database operation logging
- [x] RabbitMQ event logging
- [x] Error logging with exceptions
- [x] Warning and debug logging
- [x] Performance impact calculation
- [x] Troubleshooting guide
