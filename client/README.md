# Invoice Service Client

Dieser Client demonstriert die Verwendung des gRPC Invoice Services.

## Verwendung

```bash
# Lokal (wenn gRPC Server auf localhost:50051 läuft)
python test_client.py

# Gegen Docker Container
python test_client.py  # (conn.init nimmt host='grpc-server' wenn in Docker)
```

## Features

- ✅ Rechnungen erstellen
- ✅ Rechnungen abrufen
- ✅ Rechnungen auflisten
- ✅ Rechnungen aktualisieren
- ✅ Rechnungen löschen
- ✅ Zahlungen einleiten

## Was der Client macht

Der `test_client.py` demonstriert einen kompletten Workflow:

1. Erstellt 3 Test-Rechnungen
2. Listet alle Rechnungen auf
3. Ruft eine einzelne Rechnung ab
4. Aktualisiert eine Rechnung
5. Initiiert eine Zahlung
6. Wartet auf die Zahlungsverarbeitung (Payment Service)
7. Prüft die aktualisierte Rechnung (sollte Status "paid" haben)
8. Löscht eine Rechnung

Die einzige Abhängigkeit ist die gRPC-Stub-Datei (`app/generated/invoice_pb2.py`), 
die entweder:
- Aus dem Hauptprojekt kopiert wird, oder
- Durch Installation des gRPC-Pakets generiert wird
