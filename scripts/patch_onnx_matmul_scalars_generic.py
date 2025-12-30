#!/usr/bin/env python3
"""
Patch an ONNX file so that any MatMul node that takes a scalar Constant /
initializer becomes an elementwise Mul instead. This works around
OpenVINO's "Scalars are not supported as MatMul inputs" error.

Usage:
  python3 patch_onnx_matmul_scalars_generic.py input.onnx output_patched.onnx
"""

import sys
from pathlib import Path

import onnx
from onnx import numpy_helper, checker


def main():
    if len(sys.argv) != 3:
        print("Usage: patch_onnx_matmul_scalars_generic.py <in.onnx> <out.onnx>")
        sys.exit(1)

    in_path = Path(sys.argv[1]).resolve()
    out_path = Path(sys.argv[2]).resolve()

    if not in_path.is_file():
        print(f"❌ Input ONNX not found: {in_path}")
        sys.exit(1)

    print(f"🔹 Loading ONNX from {in_path}")
    model = onnx.load(str(in_path), load_external_data=True)
    graph = model.graph

    # ------------------------------------------------------------------
    # 1) Collect all scalar-valued tensors (initializers + Constant nodes)
    # ------------------------------------------------------------------
    scalar_names = set()

    # Initializers
    for init in graph.initializer:
        arr = numpy_helper.to_array(init)
        if arr.ndim == 0:  # scalar
            scalar_names.add(init.name)

    # Constant nodes
    for node in graph.node:
        if node.op_type == "Constant":
            for attr in node.attribute:
                if attr.name == "value":
                    arr = numpy_helper.to_array(attr.t)
                    if arr.ndim == 0:
                        # Constant has a single output
                        if node.output:
                            scalar_names.add(node.output[0])

    print(f"🔹 Found {len(scalar_names)} scalar Constant/initializer tensors")

    # ------------------------------------------------------------------
    # 2) For any MatMul that uses a scalar input, change op_type -> Mul
    # ------------------------------------------------------------------
    patched = 0
    for node in graph.node:
        if node.op_type == "MatMul":
            if any(inp in scalar_names for inp in node.input):
                node.op_type = "Mul"
                node.name = node.name + "_scalarfix"
                patched += 1

    print(f"✅ Patched {patched} MatMul nodes to Mul")

    # ------------------------------------------------------------------
    # 3) Save + run checker on the *path* (avoids >2GB ModelProto issue)
    # ------------------------------------------------------------------
    onnx.save(model, str(out_path))
    print(f"✅ Saved patched model to {out_path}")

    print("🔹 Running ONNX checker on saved path...")
    checker.check_model(str(out_path))
    print("✅ ONNX checker OK")

if __name__ == "__main__":
    main()
