# Rechnungsbearbeitung

## Architektur

### FastAPI Backend mit PostgreSQL
Ein vollständiges FastAPI Projekt mit Router, Service und Repository Schichten für die Verwaltung von Rechnungsmetadaten.

#### Projektstruktur:
```
app/
  config/
    database.py      # Datenbankkonfiguration
  models/
    invoice.py       # SQLAlchemy Modelle
  schemas/
    invoice.py       # Pydantic Schemas
  repository/
    invoice_repository.py  # Datenbankzugriffsschicht
  services/
    invoice_service.py     # Business-Logik Schicht
  routers/
    invoice_router.py      # API Endpunkte
  main.py                 # FastAPI Anwendung
```

#### Installation mit uv (empfohlen):
```shell
uv sync
# oder für Entwicklung mit dev dependencies:
uv sync --dev
```

#### Alternative Installation mit pip:
```shell
pip install -r requirements.txt
```

#### Datenbank Setup:
1. PostgreSQL Datenbank erstellen
2. `.env` Datei erstellen mit:
```
DATABASE_URL=postgresql://user:password@localhost/invoice_db
```

#### Server starten (mit uv):
```shell
uv run uvicorn app.main:app --reload
```

#### Alternative Server starten (mit pip):
```shell
uvicorn app.main:app --reload
```

#### API Endpunkte:
- `POST /invoices/` - Rechnung erstellen
- `GET /invoices/{id}` - Rechnung abrufen
- `GET /invoices/` - Alle Rechnungen abrufen
- `PUT /invoices/{id}` - Rechnung aktualisieren
- `DELETE /invoices/{id}` - Rechnung löschen

#### API Dokumentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Legacy gRPC Service (RabbitMQ)
Die alten gRPC Dateien wurden in den `legacy/` Ordner verschoben und sind nicht mehr Teil des Hauptprojekts.

- RabbitMQ als Docker Container starten:
```shell
docker run -d --hostname rabbit --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

#### Installation:
```shell
pip install grpcio grpcio-tools pika
```

#### Testen (genau diese Reihenfolge!)
1. gRPC Server starten:
```shell
python legacy/grpc_server.py
```
2. Rechnung erstellen:
```shell
python legacy/grpc_client.py
```

3. Payment Service starten:
```shell
python legacy/payment_service.py
```
4. Zahlung senden:
```shell
python legacy/payment_sender.py
```

#### Ergebnis:
- "Rechnung gespeichert" im gRPC Server
- "Zahlung verarbeitet für Rechnung 1 Betrag 100" im Payment Service