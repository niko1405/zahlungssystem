# Rechnungsbearbeitung

## Architektur
### RabbitMQ
- RabbitMQ als Docker Container starten:
- docker run -d --hostname rabbit --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
### Python
- pika = Python Client für RabbitMQ:
- pip install grpcio grpcio-tools pika