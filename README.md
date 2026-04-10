# Rechnungsbearbeitung (gRPC + RabbitMQ + Docker)

Enthaltene Komponenten:
- gRPC Server fuer Rechnungsmetadaten
- Payment Service als RabbitMQ Consumer
- PostgreSQL als Persistenz
- RabbitMQ als Message Broker
- Test-Client fuer End-to-End Ablauf

## Architektur

- gRPC Server auf Port 50051
- RabbitMQ auf Ports 5672 (AMQP) und 15672 (UI)
- PostgreSQL auf Port 5432

## Container Setup

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