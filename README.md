# Rechnungsbearbeitung (gRPC + RabbitMQ + Docker)

Moderne, verteilte Architektur für Rechnungsverarbeitung und asynchrone Zahlungsbearbeitung.

## 🏗️ Architektur-Überblick

```
┌─────────────────────────────────────────────────────────────┐
│                      TEST CLIENT                             │
│                  (client/test_client.py)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ gRPC
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              gRPC SERVER (Port 50051)                        │
│             (app/grpc_server.py)                             │
│   • CreateInvoice / GetInvoice / UpdateInvoice              │
│   • ListInvoices / DeleteInvoice                            │
│   • InitiatePayment (→ RabbitMQ)                            │
└──────┬────────────────────────────────┬─────────────────────┘
       │ SQL                            │ Publish
       ▼                                ▼
┌────────────────────┐        ┌──────────────────────────┐
│   PostgreSQL       │        │    RabbitMQ              │
│  (invoice_db)      │        │  payment_orders queue    │
│                    │        │  payment_results queue   │
└────────────────────┘        └────────┬─────────────────┘
                                       │ Consume
                                       ▼
                            ┌──────────────────────────┐
                            │  PAYMENT SERVICE         │
                            │ (app/payment_service.py) │
                            │                          │
                            │  1. Parse Message        │
                            │  2. Validate Invoice     │
                            │  3. Process Payment      │
                            │  4. Update DB            │
                            │  5. Publish Result       │
                            └──────────────────────────┘
```

---

## 📌 Die 3 Hauptkomponenten

### 1. gRPC Server (`app/grpc_server.py`)

**Zweck:** Provide gRPC endpoints für CRUD-Operationen auf Rechnungen.

**Methoden:**

| Methode | Input | Output | Beschreibung |
|---------|-------|--------|-------------|
| `CreateInvoice` | id, supplier, amount | Invoice | Neue Rechnung erstellen. Validiert, dass ID nicht doppelt existiert. |
| `GetInvoice` | id | Invoice | Einzelne Rechnung abrufen. |
| `ListInvoices` | skip, limit | [Invoice], total | Alle Rechnungen mit Pagination. |
| `UpdateInvoice` | id, supplier?, amount? | Invoice | Supplier/Amount aktualisieren (optional). |
| `DeleteInvoice` | id | success | Rechnung löschen. |
| `InitiatePayment` | invoice_id, amount, method | payment_id | Zahlung initiieren → Message in `payment_orders` Queue. |

**Workflow beispiel:**
```
Client ruft CreateInvoice auf
       ↓
gRPC Server prüft: Existiert diese ID schon?
       ↓
Falls nein: db_helpers.create_invoice() → SQLAlchemy INSERT
       ↓
StructuredLogger tracked: "DB CREATE invoice [SUCCESS] - invoice_id=INV-001"
       ↓
Protobuf Message → Client
```

---

### 2. Payment Service (`app/payment_service.py`)

**Zweck:** Asynchrone Verarbeitung von Zahlungsaufträgen via RabbitMQ.

**Workflow:**

```
RabbitMQ payment_orders Queue
       ↓
[process_payment_order] callback greift Message
       ↓
[_process_payment_message]     → JSON parsen
       ↓
[_validate_invoice]            → DB: Existiert die Rechnung?
       ↓
[_simulate_payment_processing] → Zahlung simulieren (1s delay)
       ↓
[_update_database]             → db_helpers.update_invoice_status(..., "paid")
       ↓
[_send_payment_result]         → Result in payment_results Queue publishen
       ↓
Message ACK → Bestätigung an RabbitMQ
```

**Error Handling:**
- JSON Parse Error → Message NACK (nicht requeued)
- Invoice not found → Result "failed" senden, Message ACK
- DB Update Error → Message NACK mit `requeue=True` (Retry)

---

### 3. Hilfsfunktionen (`app/utils/`)

**Lazy Logging** (`logging_config.py`):
```python
logger = StructuredLogger.for_module(__name__)
logger.log_grpc_call("CreateInvoice", status="SUCCESS", invoice_id="INV-001")
logger.log_db_operation("UPDATE", "invoice", status="SUCCESS", old_status="pending", new_status="paid")
logger.log_rabbitmq_event("MESSAGE_RECEIVED", status="IN_PROGRESS", queue="payment_orders")
```

**Database Helpers** (`db_helpers.py`):
- `create_invoice()` — Mit Existierungsprüfung
- `get_invoice_or_none()` — Safe Get
- `update_invoice_status()` — Status ändern
- `list_invoices()` — Mit Pagination
- `delete_invoice()` — Mit Validierung

**RabbitMQ Wrapper** (`rabbitmq_helpers.py`):
- `connect()` — Connection mit Retries
- `declare_queue()` — Queue sicherstellen
- `publish_message()` — Message publishen
- `setup_consumer()` — Consumer registrieren
- `start_consuming()` — Blocking Consumer Loop

---

## 🐳 Container Setup

Voraussetzungen:
- Docker
- Docker Compose Plugin

### 1. Alles bauen und starten

```bash
docker compose up -d --build
```

### 2. Status pruefen

```bash
docker compose ps
docker compose logs -f grpc-server
docker compose logs -f payment-service
```

### 3. RabbitMQ UI

```text
http://localhost:15672
user: guest
pass: guest
```

### 4. Postgres pruefen

```bash
docker compose exec postgres psql -U invoice_user -d invoice_db -c "\dt"
docker compose exec postgres psql -U invoice_user -d invoice_db -c "select * from invoices;"
```

Hinweis: Die Tabelle `invoices` wird vom gRPC Service beim Start automatisch angelegt (SQLAlchemy `create_all`).

### 5. Client ausfuehren

Lokal im Host:

```bash
python client/test_client.py
```

Wenn `python` im Host nicht gefunden wird, nutze die Projekt-venv:

Linux/macOS:

```bash
source .venv/bin/activate
python client/test_client.py
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
python client/test_client.py
```

Wenn noetig vorher in einer venv:

```bash
pip install -r requirements.txt
```

## ⌨️ Wichtige Befehle

```bash
# Start
docker compose up -d --build

# Logs
docker compose logs -f

# Stop
docker compose down

# Komplett reset inkl. DB Daten
docker compose down -v
```