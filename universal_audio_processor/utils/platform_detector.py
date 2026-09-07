import os
import platform


class PlatformDetector:
    """Detect platform capabilities without requiring optional ML packages."""

    @staticmethod
    def detect():
        info = {
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "is_rpi": False,
            "is_rpi5": False,
            "is_rpi4": False,
            "has_gpu": False,
            "gpu_name": None,
            "cpu_count": os.cpu_count() or 1,
            "total_memory_gb": PlatformDetector._get_memory_gb(),
        }
        if info["system"] == "Linux":
            info.update(PlatformDetector._check_raspberry_pi())
        info.update(PlatformDetector._check_gpu())
        return info

    @staticmethod
    def _check_raspberry_pi():
        result = {"is_rpi": False, "is_rpi5": False, "is_rpi4": False}
        try:
            with open("/proc/device-tree/model", encoding="utf-8") as model_file:
                model = model_file.read()
        except OSError:
            return result
        result["is_rpi"] = "Raspberry Pi" in model
        result["is_rpi5"] = "Raspberry Pi 5" in model
        result["is_rpi4"] = "Raspberry Pi 4" in model
        if result["is_rpi"]:
            result["rpi_model"] = model.strip()
        return result

    @staticmethod
    def _check_gpu():
        result = {"has_gpu": False, "gpu_name": None, "gpu_memory_gb": 0}
        try:
            import torch
            if torch.cuda.is_available():
                result.update({
                    "has_gpu": True,
                    "gpu_name": torch.cuda.get_device_name(0),
                    "gpu_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
                })
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                result.update({"has_gpu": True, "gpu_name": "Apple Silicon (MPS)"})
        except (ImportError, RuntimeError):
            pass
        return result

    @staticmethod
    def _get_memory_gb():
        try:
            with open("/proc/meminfo", encoding="utf-8") as memory_file:
                for line in memory_file:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / 1024 / 1024
        except (OSError, ValueError):
            return 0.0
        return 0.0

    @staticmethod
    def get_optimal_config(platform_info):
        is_edge = platform_info.get("is_rpi5") or platform_info.get("is_rpi4")
        return {
            "model_type": "onnx" if is_edge else "pytorch",
            "use_gpu": bool(platform_info.get("has_gpu") and not is_edge),
            "chunk_size": 1024 if is_edge else 2048,
            "num_threads": min(4, platform_info.get("cpu_count", 1)) if is_edge else platform_info.get("cpu_count", 1),
            "buffer_size": 5 if is_edge else 10,
        }
