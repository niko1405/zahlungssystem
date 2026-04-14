"""
Main entry point for gRPC Server
Run with: python -m grpc_service
"""

from grpc_service.grpc_server import serve

if __name__ == '__main__':
    serve()
