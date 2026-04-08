import pika
import json

def callback(ch, method, properties, body):
    data = json.loads(body)
    print(f"Zahlung verarbeitet für Rechnung {data['invoice_id']} Betrag {data['amount']}")

connection = pika.BlockingConnection(
    pika.ConnectionParameters('localhost')
)
channel = connection.channel()

channel.queue_declare(queue='payments')

channel.basic_consume(
    queue='payments',
    on_message_callback=callback,
    auto_ack=True
)

print("Warte auf Zahlungsaufträge...")
channel.start_consuming()