# SIP Gateway Service

**Phase 3: Mobile Phone Testing via Twilio**

SIP Gateway bridges traditional telephony (SIP/RTP) with the OCP Voice Platform, enabling real mobile phone testing through Twilio SIP trunks.

## Overview

The SIP Gateway service consists of two main components:

1. **FreeSWITCH Container** - Handles SIP signaling and RTP media
2. **SIP Bridge Service** - Python service that bridges FreeSWITCH to Voice Connector

## Architecture

```
Mobile Phone
    ↓ (SIP/RTP)
Twilio SIP Trunk
    ↓ (SIP/RTP via Internet)
FreeSWITCH (Port 5060, 10000-20000)
    ↓ (Event Socket Layer - Port 8021)
SIP Bridge Service (Port 8006)
    ↓ (WebSocket)
Voice Connector (Port 8005)
    ↓
[STT → Orchestrator → TTS Pipeline]
```

## Features

- ✅ Real mobile phone call support via Twilio
- ✅ SIP/RTP protocol handling with FreeSWITCH
- ✅ Audio format conversion (G.711 μ-law ↔ PCM 16-bit)
- ✅ Sample rate conversion (8 kHz ↔ 16 kHz)
- ✅ Bidirectional audio streaming
- ✅ Multiple concurrent calls (50+)
- ✅ Call management and metrics
- ✅ Health monitoring

## Quick Start

### Prerequisites

1. **Twilio Account** with:
   - Account SID
   - Auth Token
   - Phone number configured with SIP trunk

2. **Docker** and **Docker Compose** installed

3. **Network ports** available:
   - 5060 (SIP)
   - 8006 (SIP Gateway API)
   - 8021 (FreeSWITCH ESL - internal)
   - 10000-20000 (RTP media)

### Configuration

1. Update `.env` file with your Twilio credentials:

```bash
# Twilio SIP Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567
```

2. Configure Twilio SIP Trunk (in Twilio Console):
   - Go to Elastic SIP Trunking
   - Create trunk: "OCP-Platform"
   - Add Origination URI: `sip:your-server-ip:5060`
   - Assign your phone number to the trunk

### Starting the Services

```bash
# Start all services including SIP gateway
docker-compose up -d

# Or start just SIP services
docker-compose up -d freeswitch sip-gateway voice-connector stt-service tts-service orchestrator
```

### Verify Services

```bash
# Check SIP Gateway health
curl http://localhost:8006/health

# Check FreeSWITCH connection
curl http://localhost:8006/freeswitch/status

# Check active calls
curl http://localhost:8006/calls

# Check metrics
curl http://localhost:8006/metrics
```

## Testing

### Make a Test Call

1. From your mobile phone, dial your Twilio number
2. Call should connect and you'll hear a welcome message
3. Speak to interact with the voice AI
4. System will transcribe your speech, process it, and respond

### Monitor Logs

```bash
# SIP Gateway logs
docker logs -f ocp-sip-gateway

# FreeSWITCH logs
docker logs -f ocp-freeswitch

# Voice Connector logs
docker logs -f ocp-voice-connector
```

## API Endpoints

### Health Check
```bash
GET /health
```

Returns service health status and connection information.

### Active Calls
```bash
GET /calls
```

Returns list of currently active calls.

### Call Metrics
```bash
GET /metrics
```

Returns call statistics:
- Total calls
- Active calls
- Completed calls
- Average duration

### Specific Call Info
```bash
GET /calls/{unique_id}
```

Returns information about a specific call.

### FreeSWITCH Status
```bash
GET /freeswitch/status
```

Returns FreeSWITCH connection status.

## Audio Conversion

The SIP Gateway automatically handles audio format conversion:

**Inbound (Phone → Platform):**
- Input: G.711 μ-law, 8 kHz
- Output: PCM 16-bit, 16 kHz

**Outbound (Platform → Phone):**
- Input: PCM 16-bit, 16 kHz or 22.05 kHz
- Output: G.711 μ-law, 8 kHz

## Configuration

### Environment Variables

See `.env.example` for full configuration options:

- `TWILIO_ACCOUNT_SID` - Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Twilio Auth Token
- `TWILIO_PHONE_NUMBER` - Your Twilio phone number
- `FREESWITCH_ESL_PASSWORD` - FreeSWITCH ESL password (default: ClueCon)
- `MAX_CONCURRENT_CALLS` - Maximum concurrent calls (default: 50)
- `VOICE_CONNECTOR_URL` - Voice Connector WebSocket URL

## Troubleshooting

### Call Not Connecting

1. Check FreeSWITCH is running:
   ```bash
   docker ps | grep freeswitch
   ```

2. Check SIP trunk registration:
   ```bash
   docker exec -it ocp-freeswitch fs_cli -x "sofia status"
   ```

3. Verify Twilio configuration in console

### No Audio

1. Check RTP ports are open (10000-20000/udp)
2. Verify firewall rules
3. Check Voice Connector is running
4. Review audio conversion logs in SIP Gateway

### Poor Audio Quality

1. Check network latency
2. Verify codec negotiation (should be G.711 μ-law)
3. Review CPU usage on services
4. Check for packet loss

## Development

### Local Testing with ngrok

For local development, expose SIP port via ngrok:

```bash
ngrok tcp 5060
```

Use the ngrok URL in Twilio Origination URI.

### Running Tests

```bash
# Unit tests for audio converter
python -m pytest services/sip-gateway/tests/test_audio_converter.py

# Integration tests
python -m pytest services/sip-gateway/tests/
```

## Architecture Components

### FreeSWITCH
- **Purpose**: SIP/RTP protocol handling
- **Features**: Codec transcoding, NAT traversal, call routing
- **Interface**: Event Socket Layer (ESL)

### SIP Bridge Service
- **Purpose**: Bridge FreeSWITCH to Voice Connector
- **Components**:
  - `ESLHandler`: FreeSWITCH Event Socket client
  - `VoiceConnectorClient`: WebSocket client
  - `AudioConverter`: Format/sample rate conversion
  - `SIPCallBridge`: Call lifecycle management
  - `CallRouter`: Multi-call routing and management

### Audio Converter
- **G.711 ↔ PCM conversion**: Using Python `audioop`
- **Resampling**: Using `scipy.signal.resample`
- **Quality**: FFT-based resampling for best quality

## Production Deployment

### Network Configuration

For production deployment behind NAT:

1. Use `network_mode: host` in docker-compose
2. Configure external IP in FreeSWITCH
3. Or use STUN/TURN servers
4. Most SIP providers handle NAT automatically

### Firewall Rules

```bash
# SIP signaling
sudo ufw allow 5060/udp
sudo ufw allow 5060/tcp

# RTP media
sudo ufw allow 10000:20000/udp
```

### Security

- Keep Twilio credentials secure (use secrets management)
- Enable SIP authentication
- Use IP whitelisting on Twilio
- Monitor for unusual call patterns

## Performance

- **Latency**: ~2-4 seconds end-to-end (SIP + STT + NLU + TTS)
- **Concurrent Calls**: 50+ (configurable)
- **Memory**: ~100MB per call
- **CPU**: Depends on transcoding needs

## Future Enhancements

- Outbound calling
- Call recording
- DTMF support for IVR
- Multi-provider support (Vonage, Telnyx)
- WebRTC gateway
- Call analytics and quality metrics

## Support

For issues or questions:
- Check logs: `docker logs -f ocp-sip-gateway`
- Review Twilio console for SIP trunk status
- Verify FreeSWITCH registration: `fs_cli -x "sofia status"`

## License

Part of the OCP Platform project.
