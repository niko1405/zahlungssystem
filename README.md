# Rechnungsbearbeitung (gRPC + RabbitMQ + Docker)

Moderne, verteilte Architektur für Rechnungsverarbeitung und asynchrone Zahlungsbearbeitung.

## Architektur-Überblick

```text
┌─────────────────────────────────────────────────────────────┐
│                      TEST CLIENT                            │
│                  (client/test_client.py)                    │
└────────────────────────┬────────────────────────────────────┘
                         │  save invoices
                         ▼  initiate payment
┌─────────────────────────────────────────────────────────────┐
│                  gRPC SERVER - 50051                        │
│              (grpc_service/grpc_server.py)                  │
│                                                             │                       
│   • CreateInvoice / GetInvoice / UpdateInvoice              │   update invoice status
│   • ListInvoices / DeleteInvoice / UpdateInvoiceStatus      │<------------------------| 
│   • InitiatePayment (→ RabbitMQ)                            │                         │
└──────┬────────────────────────────────┬─────────────────────┘                         │
       │ SQL                            │ publish to payment_orders                     │
       ▼                                ▼                                               │
┌────────────────────┐        ┌────────────────────────────────────┐      ┌────────────────────────────┐
│ PostgreSQL - 5050  │        │        RabbitMQ - 15672            │      │  PAYMENT SERVICE - 50051   │
│                    │        │                                    │      │ (payment_service/          │
│                    │        │                                    │      │  payment_service.py)       │
│                    │        │  ┌──────────────────────────────┐  │cons. │  1. Parse Message          │
└────────────────────┘        │  │     payment_orders queue     │--│----->│  2. Validate Invoice       │
                              │  └──────────────────────────────┘  │      │  3. Process Payment        │
                              │  ┌──────────────────────────────┐  │publ. │  4. Update via gRPC        │
                              │  │    payment_results queue     │<-│------│  5. Publish Result         │
                              │  └──────────────────────────────┘  │      └────────────────────────────┘
                              └────────────────────────────────────┘

                 
```

---

## Die 3 Hauptkomponenten

### 1. gRPC Server (`grpc_service/grpc_server.py`)

**Zweck:** Provide gRPC endpoints für CRUD-Operationen auf Rechnungen.

**Methoden:**

| Methode | Input | Output | Beschreibung |
| ------- | ----- | ------ | ------------ |
| `CreateInvoice` | id, supplier, amount | Invoice | Neue Rechnung erstellen. Validiert, dass ID nicht doppelt existiert. |
| `GetInvoice` | id | Invoice | Einzelne Rechnung abrufen. |
| `ListInvoices` | skip, limit | [Invoice], total | Alle Rechnungen mit Pagination. |
| `UpdateInvoice` | id, supplier?, amount? | Invoice | Supplier/Amount aktualisieren (optional). |
| `UpdateInvoiceStatus` | id, status | Invoice | Nur den Status einer Rechnung aktualisieren. |
| `DeleteInvoice` | id | success | Rechnung löschen. |
| `InitiatePayment` | invoice_id, amount, method | payment_id | Zahlung initiieren → Message in `payment_orders` Queue. |

**Workflow beispiel:**

```text
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

### 2. Payment Service (`payment_service/payment_service.py`)

**Zweck:** Asynchrone Verarbeitung von Zahlungsaufträgen via RabbitMQ.

**Workflow:**

```text
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

### 3. Hilfsfunktionen (`utils/`)

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

## Invoice-Datenobjekt

Die fachliche Rechnung wird im Projekt an drei Stellen abgebildet:

- als SQLAlchemy-Model in `grpc_service/models/invoice.py`
- als gRPC-Message `Invoice` in `grpc_service/proto/invoice.proto`
- als Python-Objekt aus den generierten Stubs in `grpc_service/generated/invoice_pb2.py`

### Fachliche Felder

| Feld | Typ | Beschreibung |
| ---- | --- | ------------ |
| `id` | `string` | Eindeutige Rechnungs-ID |
| `supplier` | `string` | Lieferant oder Rechnungsaussteller |
| `amount` | `double` | Rechnungsbetrag |
| `created_at` | `string` | Erstellzeitpunkt als ISO-String |
| `updated_at` | `string` | Letzte Änderung als ISO-String |
| `status` | `string` | Status der Rechnung, z. B. `pending`, `paid`, `cancelled` |

### Lebenszyklus im System

```text
Client sendet CreateInvoice
       ↓
gRPC Server erstellt Invoice-Objekt
       ↓
SQLAlchemy speichert in PostgreSQL
       ↓
GetInvoice / ListInvoices lesen dieselben Felder wieder aus
       ↓
Payment Service aktualisiert nur den Status über gRPC
```

### Beispielstruktur

```python
{
    "id": "INV-001",
    "supplier": "Acme Corp",
    "amount": 1250.0,
    "created_at": "2026-04-10T13:00:00+00:00",
    "updated_at": "2026-04-10T13:05:00+00:00",
    "status": "paid"
}
```

---

## Container Setup

Voraussetzungen:

- Docker
- Docker Compose Plugin

### 1. Alles bauen und starten

```bash
docker compose up -d --build
```

### 2. Status der Container prüfen

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

### 4. pgAdmin für PostgreSQL

```text
http://localhost:5050
email: admin@example.com
pass: admin123
```

Nach dem Login den PostgreSQL-Server manuell anlegen:

- Host: `postgres`
- Port: `5432`
- Maintenance DB: `invoice_db`
- User: `invoice_user`
- Password: `invoice_password`

### 5. Postgres prüfen

```bash
docker compose exec postgres psql -U invoice_user -d invoice_db -c "\dt"
docker compose exec postgres psql -U invoice_user -d invoice_db -c "select * from invoices;"
```

Hinweis: Die Tabelle `invoices` wird vom gRPC Service beim Start automatisch angelegt (SQLAlchemy `create_all`).

### 6. Client ausführen

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

Wenn nötig vorher in einer venv:

```bash
pip install -r requirements.txt
```

## Wichtige Befehle

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
