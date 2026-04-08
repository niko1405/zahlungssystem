import grpc
import invoice_pb2
import invoice_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = invoice_pb2_grpc.InvoiceServiceStub(channel)

    response = stub.CreateInvoice(
        invoice_pb2.InvoiceRequest(
            id="1",
            supplier="Lieferant A",
            amount=100.0
        )
    )

    print("Server Antwort:", response.status)


if __name__ == "__main__":
    run()