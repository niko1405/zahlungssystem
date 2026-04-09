import pika
import json

connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

channel.queue_declare(queue='payments')

message = {
    "invoice_id": "1",
    "amount": 100.0
}

channel.basic_publish(
    exchange='',
    routing_key='payments',
    body=json.dumps(message)
)

print("Zahlungsauftrag gesendet")

connection.close()