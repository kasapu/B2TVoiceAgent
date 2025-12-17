"""
Audio Converter Service
Handles conversion between G.711 μ-law codec and PCM, and resampling between 8kHz and 16kHz
"""
import audioop
import numpy as np
from scipy import signal
from typing import Literal


class AudioConverter:
    """
    Audio format and sample rate converter for SIP gateway

    Supports:
    - G.711 μ-law/a-law <-> 16-bit PCM conversion
    - Sample rate conversion (8kHz <-> 16kHz)
    """

    @staticmethod
    def g711_to_pcm16(audio_data: bytes, law: Literal['ulaw', 'alaw'] = 'ulaw') -> bytes:
        """
        Convert G.711 μ-law or a-law to 16-bit PCM

        Args:
            audio_data: G.711 encoded audio bytes
            law: Codec type ('ulaw' for μ-law, 'alaw' for a-law)

        Returns:
            16-bit PCM audio bytes
        """
        if not audio_data:
            return b''

        try:
            if law == 'ulaw':
                # Convert μ-law to linear PCM (16-bit)
                pcm_data = audioop.ulaw2lin(audio_data, 2)  # 2 bytes = 16-bit
            elif law == 'alaw':
                # Convert a-law to linear PCM (16-bit)
                pcm_data = audioop.alaw2lin(audio_data, 2)
            else:
                raise ValueError(f"Unsupported law type: {law}. Use 'ulaw' or 'alaw'")

            return pcm_data
        except Exception as e:
            raise ValueError(f"Failed to convert G.711 to PCM: {str(e)}")

    @staticmethod
    def pcm16_to_g711(audio_data: bytes, law: Literal['ulaw', 'alaw'] = 'ulaw') -> bytes:
        """
        Convert 16-bit PCM to G.711 μ-law or a-law

        Args:
            audio_data: 16-bit PCM audio bytes
            law: Codec type ('ulaw' for μ-law, 'alaw' for a-law)

        Returns:
            G.711 encoded audio bytes
        """
        if not audio_data:
            return b''

        try:
            if law == 'ulaw':
                # Convert linear PCM to μ-law
                g711_data = audioop.lin2ulaw(audio_data, 2)  # 2 bytes = 16-bit
            elif law == 'alaw':
                # Convert linear PCM to a-law
                g711_data = audioop.lin2alaw(audio_data, 2)
            else:
                raise ValueError(f"Unsupported law type: {law}. Use 'ulaw' or 'alaw'")

            return g711_data
        except Exception as e:
            raise ValueError(f"Failed to convert PCM to G.711: {str(e)}")

    @staticmethod
    def resample(
        audio_data: bytes,
        from_rate: int,
        to_rate: int,
        channels: int = 1
    ) -> bytes:
        """
        Resample audio from one sample rate to another

        Args:
            audio_data: 16-bit PCM audio bytes
            from_rate: Source sample rate (Hz)
            to_rate: Target sample rate (Hz)
            channels: Number of audio channels (default: 1 for mono)

        Returns:
            Resampled 16-bit PCM audio bytes
        """
        if not audio_data:
            return b''

        if from_rate == to_rate:
            return audio_data  # No resampling needed

        try:
            # Convert bytes to numpy array (16-bit signed integers)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # For stereo, reshape array
            if channels == 2:
                audio_array = audio_array.reshape((-1, 2))

            # Calculate number of output samples
            num_samples = int(len(audio_array) * to_rate / from_rate)

            # Resample using scipy.signal.resample
            # This uses FFT-based resampling for better quality
            if channels == 1:
                resampled = signal.resample(audio_array, num_samples)
            else:
                # Resample each channel separately for stereo
                resampled_left = signal.resample(audio_array[:, 0], num_samples)
                resampled_right = signal.resample(audio_array[:, 1], num_samples)
                resampled = np.column_stack((resampled_left, resampled_right))

            # Convert back to 16-bit integers and clip to prevent overflow
            resampled_int16 = np.clip(resampled, -32768, 32767).astype(np.int16)

            # Convert back to bytes
            return resampled_int16.tobytes()

        except Exception as e:
            raise ValueError(f"Failed to resample audio: {str(e)}")

    @staticmethod
    def convert_sip_to_platform(audio_data: bytes, sip_sample_rate: int = 8000) -> bytes:
        """
        Convert SIP audio (G.711 μ-law 8kHz) to platform format (PCM 16kHz)

        This is a convenience method that combines codec conversion and resampling.

        Args:
            audio_data: G.711 μ-law encoded audio bytes at 8kHz
            sip_sample_rate: SIP audio sample rate (default: 8000 Hz)

        Returns:
            16-bit PCM audio bytes at 16kHz
        """
        if not audio_data:
            return b''

        # Step 1: Convert G.711 μ-law to PCM 16-bit
        pcm_data = AudioConverter.g711_to_pcm16(audio_data, law='ulaw')

        # Step 2: Resample from 8kHz to 16kHz
        platform_data = AudioConverter.resample(
            pcm_data,
            from_rate=sip_sample_rate,
            to_rate=16000
        )

        return platform_data

    @staticmethod
    def convert_platform_to_sip(audio_data: bytes, platform_sample_rate: int = 16000) -> bytes:
        """
        Convert platform audio (PCM 16kHz or 22.05kHz) to SIP format (G.711 μ-law 8kHz)

        This is a convenience method that combines resampling and codec conversion.

        Args:
            audio_data: 16-bit PCM audio bytes at 16kHz or 22.05kHz
            platform_sample_rate: Platform audio sample rate (default: 16000 Hz)

        Returns:
            G.711 μ-law encoded audio bytes at 8kHz
        """
        if not audio_data:
            return b''

        # Step 1: Resample to 8kHz
        resampled_data = AudioConverter.resample(
            audio_data,
            from_rate=platform_sample_rate,
            to_rate=8000
        )

        # Step 2: Convert PCM 16-bit to G.711 μ-law
        sip_data = AudioConverter.pcm16_to_g711(resampled_data, law='ulaw')

        return sip_data

    @staticmethod
    def get_audio_duration(audio_data: bytes, sample_rate: int, sample_width: int = 2) -> float:
        """
        Calculate audio duration in seconds

        Args:
            audio_data: Audio bytes
            sample_rate: Sample rate in Hz
            sample_width: Bytes per sample (default: 2 for 16-bit)

        Returns:
            Duration in seconds
        """
        if not audio_data:
            return 0.0

        num_samples = len(audio_data) // sample_width
        duration = num_samples / sample_rate
        return duration
