import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from private_reading.core.tts_client import TTSClient
from private_reading.exceptions import TTSAPIError

@pytest.mark.asyncio
async def test_fish_payload():
    endpoint = "http://fish-tts/v1/tts"
    client = TTSClient(
        endpoint=endpoint,
        provider="fish",
        reference_id="ref123",
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.2
    )
    
    # Mock ClientSession.post
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b"audio data"
    
    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.close = AsyncMock()
    
    with patch('private_reading.core.tts_client.ClientSession', return_value=mock_session):
        async with client:
            await client.generate_speech("Hello world")
            
            # Verify payload
            args, kwargs = mock_session.post.call_args
            assert args[0] == endpoint
            payload = kwargs['json']
            assert payload["text"] == "Hello world"
            assert payload["format"] == "wav"
            assert payload["reference_id"] == "ref123"
            assert payload["temperature"] == 0.7
            assert payload["top_p"] == 0.9
            assert payload["repetition_penalty"] == 1.2
            assert payload["streaming"] is False

@pytest.mark.asyncio
async def test_qwen_payload():
    endpoint = "http://qwen-tts/v1/audio/speech"
    client = TTSClient(
        endpoint=endpoint,
        provider="qwen",
        voice="A deep voice",
        model="qwen-v3",
        reference_id="ref456",
        temperature=0.5
    )
    
    # Mock ClientSession.post
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b"audio data"
    
    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response
    mock_session.close = AsyncMock()
    
    with patch('private_reading.core.tts_client.ClientSession', return_value=mock_session):
        async with client:
            await client.generate_speech("Hello world")
            
            # Verify payload
            args, kwargs = mock_session.post.call_args
            assert args[0] == endpoint
            payload = kwargs['json']
            assert payload["input"] == "Hello world"
            assert payload["model"] == "qwen-v3"
            assert payload["response_format"] == "wav"
            assert payload["voice"] == "A deep voice"
            assert payload["reference_id"] == "ref456"
            assert payload["temperature"] == 0.5
            assert "top_p" not in payload
