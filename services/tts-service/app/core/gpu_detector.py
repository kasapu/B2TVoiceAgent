"""GPU detection utility for automatic device selection."""

import logging

logger = logging.getLogger(__name__)


def detect_device() -> str:
    """
    Detect if CUDA GPU is available and return appropriate device.

    Returns:
        str: "cuda" if GPU available, "cpu" otherwise
    """
    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU detected: {gpu_name}")
            logger.info("Using CUDA device for TTS synthesis")
            return "cuda"
        else:
            logger.info("No GPU detected, using CPU")
            return "cpu"
    except ImportError:
        logger.warning("PyTorch not installed, defaulting to CPU")
        return "cpu"
    except Exception as e:
        logger.error(f"Error detecting GPU: {e}")
        logger.info("Falling back to CPU")
        return "cpu"


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
                "cuda_version": torch.version.cuda
            }
        else:
            return {
                "device": "cpu",
                "device_name": "CPU",
                "device_count": 1
            }
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return {
            "device": "cpu",
            "device_name": "CPU (fallback)",
            "error": str(e)
        }
