"""
SIP Gateway Service Configuration
"""
import os
from typing import Optional, Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service Info
    SERVICE_NAME: str = "OCP SIP Gateway"
    VERSION: str = "1.0.0"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8006"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Voice Connector Service (WebSocket client)
    VOICE_CONNECTOR_URL: str = os.getenv(
        "VOICE_CONNECTOR_URL",
        "ws://voice-connector:8005"
    )

    # FreeSWITCH Configuration
    FREESWITCH_HOST: str = os.getenv("FREESWITCH_HOST", "freeswitch")
    FREESWITCH_ESL_PORT: int = int(os.getenv("FREESWITCH_ESL_PORT", "8021"))
    FREESWITCH_ESL_PASSWORD: str = os.getenv("FREESWITCH_ESL_PASSWORD", "ClueCon")

    # Twilio SIP Trunk Configuration
    SIP_PROVIDER: Literal['twilio', 'vonage', 'telnyx', 'custom'] = os.getenv(
        "SIP_PROVIDER", "twilio"
    )
    TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: Optional[str] = os.getenv("TWILIO_PHONE_NUMBER")

    # Generic SIP Configuration (for other providers)
    SIP_TRUNK_URI: Optional[str] = os.getenv("SIP_TRUNK_URI")
    SIP_USERNAME: Optional[str] = os.getenv("SIP_USERNAME")
    SIP_PASSWORD: Optional[str] = os.getenv("SIP_PASSWORD")
    SIP_REALM: Optional[str] = os.getenv("SIP_REALM")

    # Audio Configuration
    SIP_SAMPLE_RATE: int = int(os.getenv("SIP_SAMPLE_RATE", "8000"))  # 8kHz for telephony
    PLATFORM_SAMPLE_RATE: int = int(os.getenv("PLATFORM_SAMPLE_RATE", "16000"))  # 16kHz for platform
    CODEC_PREFERENCE: str = os.getenv("CODEC_PREFERENCE", "PCMU")  # G.711 μ-law
    AUDIO_CHUNK_SIZE: int = int(os.getenv("AUDIO_CHUNK_SIZE", "160"))  # 20ms at 8kHz

    # Call Management
    MAX_CONCURRENT_CALLS: int = int(os.getenv("MAX_CONCURRENT_CALLS", "50"))
    CALL_TIMEOUT_SECONDS: int = int(os.getenv("CALL_TIMEOUT_SECONDS", "3600"))  # 1 hour max

    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_TIMEOUT: int = int(os.getenv("WS_TIMEOUT", "300"))
    WS_RECONNECT_DELAY: int = int(os.getenv("WS_RECONNECT_DELAY", "5"))

    # RTP Configuration
    RTP_PORT_RANGE_START: int = int(os.getenv("RTP_PORT_RANGE_START", "10000"))
    RTP_PORT_RANGE_END: int = int(os.getenv("RTP_PORT_RANGE_END", "20000"))

    # Logging
    ENABLE_DETAILED_LOGGING: bool = os.getenv("ENABLE_DETAILED_LOGGING", "false").lower() == "true"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
