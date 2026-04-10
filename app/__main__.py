"""
Main entry point for gRPC Server
Run with: python -m app.grpc_server
"""

from app.grpc_server import serve

if __name__ == '__main__':
    serve()
