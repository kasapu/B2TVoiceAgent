"""GPU detection utility for automatic device selection."""

import logging

logger = logging.getLogger(__name__)


def detect_device() -> tuple[str, str]:
    """
    Detect if CUDA GPU is available and return appropriate device and compute type.

    Returns:
        tuple: (device, compute_type)
            - device: "cuda" if GPU available, "cpu" otherwise
            - compute_type: "float16" for GPU, "int8" for CPU
    """
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU detected: {gpu_name}")
            logger.info("Using CUDA device with float16 precision")
            return "cuda", "float16"
        else:
            logger.info("No GPU detected, using CPU")
            logger.info("Using CPU device with int8 precision")
            return "cpu", "int8"
    except ImportError:
        logger.warning("PyTorch not installed, defaulting to CPU")
        return "cpu", "int8"
    except Exception as e:
        logger.error(f"Error detecting GPU: {e}")
        logger.info("Falling back to CPU")
        return "cpu", "int8"


def get_device_info() -> dict:
    """
    Get detailed information about the compute device.

    Returns:
        dict: Device information including name, type, memory, etc.
    """
    try:
        import torch

        if torch.cuda.is_available():
            return {
                "device": "cuda",
                "device_name": torch.cuda.get_device_name(0),
                "device_count": torch.cuda.device_count(),
                "memory_total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
                "cuda_version": torch.version.cuda,
                "compute_type": "float16"
            }
        else:
            return {
                "device": "cpu",
                "device_name": "CPU",
                "device_count": 1,
                "compute_type": "int8"
            }
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {
            "device": "cpu",
            "device_name": "CPU (fallback)",
            "error": str(e)
        }
