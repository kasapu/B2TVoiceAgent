"""
Audio Buffer for Voice Connector
Handles audio chunk buffering and Voice Activity Detection (VAD)
"""
import asyncio
import numpy as np
from typing import Optional, List
from io import BytesIO
import wave
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AudioBuffer:
    """
    Buffers incoming audio chunks and detects voice activity
    to determine when to send for transcription
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 4096,
        buffer_duration_ms: int = 1000,
        silence_threshold: float = 0.01,
        silence_duration_ms: int = 500,
    ):
        """
        Initialize audio buffer

        Args:
            sample_rate: Audio sample rate in Hz
            chunk_size: Size of each audio chunk in bytes
            buffer_duration_ms: Maximum buffer duration in milliseconds
            silence_threshold: RMS threshold for silence detection
            silence_duration_ms: Duration of silence to trigger flush
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.buffer_duration_ms = buffer_duration_ms
        self.silence_threshold = silence_threshold
        self.silence_duration_ms = silence_duration_ms

        # Internal state
        self.chunks: List[bytes] = []
        self.silence_chunks = 0
        self.total_duration_ms = 0

        # Calculate thresholds
        self.max_chunks = int(
            (buffer_duration_ms / 1000) * sample_rate * 2 / chunk_size
        )
        self.silence_chunk_threshold = int(
            (silence_duration_ms / 1000) * sample_rate * 2 / chunk_size
        )

        logger.info(
            f"AudioBuffer initialized: sample_rate={sample_rate}, "
            f"chunk_size={chunk_size}, max_chunks={self.max_chunks}"
        )

    def add_chunk(self, audio_data: bytes) -> None:
        """
        Add an audio chunk to the buffer

        Args:
            audio_data: Raw audio bytes
        """
        self.chunks.append(audio_data)

        # Calculate duration
        chunk_duration_ms = (len(audio_data) / 2) / self.sample_rate * 1000
        self.total_duration_ms += chunk_duration_ms

        # Check if chunk contains silence
        if self._is_silent(audio_data):
            self.silence_chunks += 1
        else:
            self.silence_chunks = 0

    def should_flush(self) -> bool:
        """
        Determine if buffer should be flushed

        Returns:
            True if buffer should be flushed
        """
        # Flush if buffer is full
        if len(self.chunks) >= self.max_chunks:
            logger.debug("Buffer full, should flush")
            return True

        # Flush if silence detected after speech
        if (
            len(self.chunks) > 0
            and self.silence_chunks >= self.silence_chunk_threshold
        ):
            logger.debug(f"Silence detected ({self.silence_chunks} chunks), should flush")
            return True

        return False

    def get_audio(self) -> Optional[bytes]:
        """
        Get buffered audio as WAV bytes

        Returns:
            WAV audio bytes or None if buffer is empty
        """
        if not self.chunks:
            return None

        try:
            # Combine all chunks
            audio_data = b"".join(self.chunks)

            # Convert to WAV format
            wav_bytes = self._to_wav(audio_data)

            logger.info(
                f"Retrieved {len(self.chunks)} chunks, "
                f"total {len(wav_bytes)} bytes, "
                f"duration {self.total_duration_ms:.0f}ms"
            )

            return wav_bytes

        except Exception as e:
            logger.error(f"Error getting audio from buffer: {e}")
            return None

    def clear(self) -> None:
        """Clear the buffer"""
        logger.debug(f"Clearing buffer ({len(self.chunks)} chunks)")
        self.chunks.clear()
        self.silence_chunks = 0
        self.total_duration_ms = 0

    def _is_silent(self, audio_data: bytes) -> bool:
        """
        Check if audio chunk is silent using RMS

        Args:
            audio_data: Raw audio bytes

        Returns:
            True if silent
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Calculate RMS (Root Mean Square)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))

            # Normalize to 0-1 range
            normalized_rms = rms / 32768.0

            is_silent = normalized_rms < self.silence_threshold

            return is_silent

        except Exception as e:
            logger.error(f"Error calculating silence: {e}")
            return False

    def _to_wav(self, audio_data: bytes) -> bytes:
        """
        Convert raw PCM audio to WAV format

        Args:
            audio_data: Raw PCM audio bytes

        Returns:
            WAV format audio bytes
        """
        wav_buffer = BytesIO()

        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)

        return wav_buffer.getvalue()

    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return len(self.chunks) == 0

    @property
    def duration_ms(self) -> float:
        """Get current buffer duration in milliseconds"""
        return self.total_duration_ms

    @property
    def chunk_count(self) -> int:
        """Get number of chunks in buffer"""
        return len(self.chunks)
