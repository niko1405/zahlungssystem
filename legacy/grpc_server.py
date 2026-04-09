import grpc
from concurrent import futures
import invoice_pb2
import invoice_pb2_grpc

invoices = {}

class InvoiceService(invoice_pb2_grpc.InvoiceServiceServicer):
    def CreateInvoice(self, request, context):
        invoices[request.id] = {
            "supplier": request.supplier,
            "amount": request.amount
        }
        print(f"Rechnung gespeichert: {request.id}")

        return invoice_pb2.InvoiceResponse(status="OK")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    invoice_pb2_grpc.add_InvoiceServiceServicer_to_server(InvoiceService(), server)

    server.add_insecure_port('[::]:50051')
    server.start()
    print("gRPC Server läuft auf Port 50051...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()