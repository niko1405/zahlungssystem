#!/bin/bash
# Generate gRPC Python code from protobuf files

set -e

echo "🔨 Generating gRPC Python code from protobuf files..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

# Generate invoice service
"$PYTHON_BIN" -m grpc_tools.protoc \
  -I./app/proto \
  --python_out=./app \
  --grpc_python_out=./app \
  ./app/proto/invoice.proto

# Generate payment messages
"$PYTHON_BIN" -m grpc_tools.protoc \
  -I./app/proto \
  --python_out=./app \
  --grpc_python_out=./app \
  ./app/proto/payment.proto

echo "✅ gRPC code generation completed!"
echo "Generated files:"
echo "  - app/invoice_pb2.py"
echo "  - app/invoice_pb2_grpc.py"
echo "  - app/payment_pb2.py"
echo "  - app/payment_pb2_grpc.py"
