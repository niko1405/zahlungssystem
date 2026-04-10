#!/bin/bash
# Generate gRPC Python code from protobuf files

set -e

echo "🔨 Generating gRPC Python code from protobuf files..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

GEN_DIR="$SCRIPT_DIR/app/generated"
mkdir -p "$GEN_DIR"
touch "$GEN_DIR/__init__.py"

if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

# Generate invoice service
"$PYTHON_BIN" -m grpc_tools.protoc \
  -I./app/proto \
  --python_out="$GEN_DIR" \
  --grpc_python_out="$GEN_DIR" \
  ./app/proto/invoice.proto

# Generate payment messages
"$PYTHON_BIN" -m grpc_tools.protoc \
  -I./app/proto \
  --python_out="$GEN_DIR" \
  --grpc_python_out="$GEN_DIR" \
  ./app/proto/payment.proto

# Ensure generated grpc stub resolves module from the same package.
sed -i 's/^import invoice_pb2 as/from . import invoice_pb2 as/' "$GEN_DIR/invoice_pb2_grpc.py"

echo "✅ gRPC code generation completed!"
echo "Generated files:"
echo "  - app/generated/invoice_pb2.py"
echo "  - app/generated/invoice_pb2_grpc.py"
echo "  - app/generated/payment_pb2.py"
echo "  - app/generated/payment_pb2_grpc.py"
