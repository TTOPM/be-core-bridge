# File: belel_sing_gen/belel_onnx_exporter.py
# Purpose: One-time export of BELEL core models to ONNX + TensorRT engines
# Features:
#   - Exports diffusion UNet or full pipeline to ONNX (opset 17)
#   - Builds TensorRT engine (FP16/INT8) for 2–4× speedup
#   - Dynamic shapes for variable-length generation
#   - Model validation + inference test
#   - Saves engines ready for production use
# Dependencies: torch, onnx, onnxruntime, tensorrt (pip install tensorrt onnxruntime-gpu)

import torch
import onnx
import onnxruntime as ort
from pathlib import Path
import numpy as np
import os
import argparse
import time

# Optional TensorRT (comment out if not installed)
try:
    import tensorrt as trt
    TRT_AVAILABLE = True
except ImportError:
    TRT_AVAILABLE = False
    print("TensorRT not found — skipping engine build (install tensorrt package)")

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

SAMPLE_RATE = 44100
MODEL_OPSET = 17
DYNAMIC_AXES = {
    "latent": {0: "batch", 2: "time"},     # Allow variable batch & length
    "output": {0: "batch", 2: "time"}
}
DEFAULT_ENGINE_PATH = Path("engines/belel_rectflow_dit.engine")
DEFAULT_ONNX_PATH = Path("models/belel_rectflow_dit.onnx")

# Dummy input shapes (adjust to your actual model)
DUMMY_LATENT_SHAPE = (1, 4, 256, 256)   # Example for latent diffusion
DUMMY_OUTPUT_SHAPE = (1, 1, 44100 * 180)  # 3 min at 44.1 kHz

# ────────────────────────────────────────────────
# EXPORT FUNCTIONS
# ────────────────────────────────────────────────

def export_to_onnx(
    model: torch.nn.Module,
    dummy_input: torch.Tensor,
    onnx_path: Path = DEFAULT_ONNX_PATH,
    opset_version: int = MODEL_OPSET
):
    """Export PyTorch model to ONNX with dynamic shapes."""
    print(f"Exporting model to ONNX → {onnx_path}")

    model.eval()
    model.to("cpu")  # Export on CPU to avoid device issues

    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["latent"],
        output_names=["output"],
        dynamic_axes=DYNAMIC_AXES
    )

    # Validate ONNX model
    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    print("ONNX model validated successfully")

def build_tensorrt_engine(
    onnx_path: Path,
    engine_path: Path = DEFAULT_ENGINE_PATH,
    fp16: bool = True,
    int8: bool = False,
    max_batch_size: int = 4,
    workspace_size_gb: int = 8
):
    """Build TensorRT engine from ONNX for ultra-fast inference."""
    if not TRT_AVAILABLE:
        print("TensorRT not installed — skipping engine build")
        return

    print(f"Building TensorRT engine → {engine_path}")
    print(f"  Precision: {'INT8' if int8 else 'FP16' if fp16 else 'FP32'}")
    print(f"  Max batch: {max_batch_size} | Workspace: {workspace_size_gb} GB")

    TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(TRT_LOGGER)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, TRT_LOGGER)

    with open(str(onnx_path), 'rb') as model_file:
        if not parser.parse(model_file.read()):
            print("ERROR: Failed to parse ONNX")
            for error in range(parser.num_errors):
                print(parser.get_error(error))
            return

    config = builder.create_builder_config()
    config.max_workspace_size = workspace_size_gb * (1 << 30)  # GB to bytes

    if fp16 and builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
    if int8 and builder.platform_has_fast_int8:
        config.set_flag(trt.BuilderFlag.INT8)

    config.max_batch_size = max_batch_size

    engine = builder.build_engine(network, config)
    if engine is None:
        print("ERROR: Failed to build TensorRT engine")
        return

    with open(str(engine_path), "wb") as f:
        f.write(engine.serialize())

    print(f"TensorRT engine saved to: {engine_path}")
    print("Ready for ultra-fast inference with TensorRT runtime")

def test_onnx_inference(onnx_path: Path, dummy_input_np: np.ndarray):
    """Quick validation run with ONNX Runtime."""
    print("Testing ONNX inference speed...")
    sess = ort.InferenceSession(str(onnx_path), providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

    start = time.time()
    outputs = sess.run(None, {"latent": dummy_input_np})
    elapsed = time.time() - start

    print(f"ONNX inference time: {elapsed*1000:.2f} ms")
    print(f"Output shape: {outputs[0].shape}")

# ────────────────────────────────────────────────
# CLI ENTRY POINT
# ────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BELEL ONNX + TensorRT Exporter")
    parser.add_argument("--model", type=str, required=True, help="Path to PyTorch model .pt or .pth")
    parser.add_argument("--output_onnx", type=str, default=str(DEFAULT_ONNX_PATH), help="ONNX output path")
    parser.add_argument("--output_engine", type=str, default=str(DEFAULT_ENGINE_PATH), help="TensorRT engine path")
    parser.add_argument("--fp16", action="store_true", help="Enable FP16 TensorRT")
    parser.add_argument("--int8", action="store_true", help="Enable INT8 TensorRT (calibration needed)")
    parser.add_argument("--test", action="store_true", help="Run quick inference test after export")
    parser.add_argument("--batch", type=int, default=1, help="Max batch size for TensorRT")
    parser.add_argument("--workspace_gb", type=int, default=8, help="TensorRT workspace size (GB)")

    args = parser.parse_args()

    # Load your model (replace with your actual loading logic)
    # Example: diffusion UNet from your pipeline
    model = torch.load(args.model, map_location="cpu")  # <-- REPLACE WITH REAL LOAD
    model.eval()

    # Dummy input (adjust shape to match your model's expected input)
    dummy_input = torch.randn(1, 4, 256, 256)  # Example latent shape

    # Export ONNX
    export_to_onnx(model, dummy_input, Path(args.output_onnx))

    # Build TensorRT engine if available
    if TRT_AVAILABLE:
        build_tensorrt_engine(
            Path(args.output_onnx),
            Path(args.output_engine),
            fp16=args.fp16,
            int8=args.int8,
            max_batch_size=args.batch,
            workspace_size_gb=args.workspace_gb
        )

    # Quick test
    if args.test:
        dummy_np = dummy_input.cpu().numpy()
        test_onnx_inference(Path(args.output_onnx), dummy_np)

    print("\nExport complete!")
    print("Use ONNX Runtime or TensorRT runtime for inference in production.")
    print("Example ONNX Runtime usage:")
    print("  sess = ort.InferenceSession('models/belel_rectflow_dit.onnx')")
    print("  output = sess.run(None, {'latent': your_latent_np})[0]")
