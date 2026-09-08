import httpx
from ..core.config import settings
class ElevenLabsProvider:
    async def synthesize(self,text):
        if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
            raise RuntimeError("ElevenLabs is not configured")
        url=f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
        async with httpx.AsyncClient(timeout=60) as c:
            r=await c.post(url,headers={"xi-api-key":settings.elevenlabs_api_key,"Content-Type":"application/json"},json={"text":text})
            r.raise_for_status(); return r.content
