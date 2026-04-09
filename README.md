# Rechnungsbearbeitunggggg

## Architektur
### RabbitMQ
- RabbitMQ als Docker Container starten:
```shell
docker run -d --hostname rabbit --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```
### Python
- pika = Python Client für RabbitMQ:
```shell
pip install grpcio grpcio-tools pika
```
### Testen (genau diese Reihenfolge!)
- 1. gRPC Server starten
```shell
python grpc_server.py
```
- 2. Rechnung erstellen
```shell
python grpc_client.py
```

👉 Ausgabe: „Rechnung gespeichert“

- 3. Payment Service starten
```shell
python payment_service.py
```
- 4. Zahlung senden
```shell
- python payment_sender.py
```

👉 Ergebnis im Payment Service:

- Zahlung verarbeitet für Rechnung 1 Betrag 100