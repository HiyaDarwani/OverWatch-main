from core.universal_interface import AudioIOInterface, FileIO, MicrophoneIO


class IOFactory:
    """Create an audio adapter from a simple configuration name."""

    @staticmethod
    def create_io(io_type, **kwargs) -> AudioIOInterface:
        if io_type == "file":
            return FileIO(**kwargs)
        if io_type == "microphone":
            return MicrophoneIO(**kwargs)
        raise ValueError(f"Unsupported I/O type: {io_type}")

    @staticmethod
    def auto_detect_io(**kwargs) -> AudioIOInterface:
        if kwargs.get("input_file"):
            return FileIO(
                input_path=kwargs["input_file"],
                output_path=kwargs.get("output_file"),
                chunk_size=kwargs.get("chunk_size", 1024),
                sample_rate=kwargs.get("sample_rate", 16000),
            )
        return MicrophoneIO(
            sample_rate=kwargs.get("sample_rate", 16000),
            chunk_size=kwargs.get("chunk_size", 1024),
        )
