import json
import logging
from pathlib import Path
from typing import Optional
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openrouter_client")

def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR     = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"

def _load_gemini_key() -> str:
    try:
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("gemini_api_key", "").strip()
        if not key:
            raise ValueError("gemini_api_key is empty in api_keys.json")
        return key
    except Exception as e:
        logger.error(f"Failed to load Gemini API key: {e}")
        return ""

# Initialize Gemini with the API key
genai.configure(api_key=_load_gemini_key())
MODEL_NAME = "models/gemini-3.8-flash"

class OpenRouterClient:
    def chat(
        self,
        prompt: str,
        system: str = "You are a component of LIHA, an intelligent AI assistant. Be concise, helpful, and precise.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        for m_name in [model or MODEL_NAME, "models/gemini-3.5-flash", "models/gemini-3.1-flash-lite", "models/gemini-flash-latest"]:
            try:
                gen_model = genai.GenerativeModel(
                    m_name,
                    system_instruction=system,
                    generation_config={"max_output_tokens": max_tokens, "temperature": temperature}
                )
                response = gen_model.generate_content(prompt)
                if response and response.text:
                    return response.text
            except Exception:
                continue
        return ""

    def chat_json(
        self,
        prompt: str,
        system: str = "Return ONLY valid JSON. No markdown fences, no extra text, no explanation.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> dict:
        gen_model = genai.GenerativeModel(
            MODEL_NAME,
            system_instruction=system,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        )
        response = gen_model.generate_content(prompt)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] JSON parse failed: {e}\nRaw response: {response.text}")
            raise ValueError(f"Model returned unparseable JSON: {e}")

    def vision(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/png",
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        gen_model = genai.GenerativeModel(
            MODEL_NAME,
            system_instruction=system,
            generation_config={"max_output_tokens": max_tokens, "temperature": 0.2}
        )
        response = gen_model.generate_content([
            {"mime_type": mime, "data": image_b64},
            prompt
        ])
        return response.text

    def vision_from_file(
        self,
        prompt: str,
        image_path: str,
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        path = Path(image_path)
        mime_map = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif":  "image/gif",
        }
        mime = mime_map.get(path.suffix.lower(), "image/png")
        
        import base64
        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        return self.vision(prompt, image_b64, mime, system, model, max_tokens)

    def multi_turn(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        
        system_instruction = "You are a helpful assistant."
        history = []
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
            elif m["role"] == "user":
                history.append({"role": "user", "parts": [m["content"]]})
            elif m["role"] == "assistant":
                history.append({"role": "model", "parts": [m["content"]]})
                
        gen_model = genai.GenerativeModel(
            MODEL_NAME,
            system_instruction=system_instruction,
            generation_config={"max_output_tokens": max_tokens, "temperature": temperature}
        )
        
        # Pop the last message to send as the new message
        if history and history[-1]["role"] == "user":
            last_user_msg = history.pop()["parts"][0]
        else:
            last_user_msg = ""
            
        chat = gen_model.start_chat(history=history)
        response = chat.send_message(last_user_msg)
        return response.text

    def available_models(self) -> dict:
        return {
            "text_models":   [MODEL_NAME],
            "vision_models": [MODEL_NAME],
            "rate_limited":  [],
            "total_text":    1,
            "total_vision":  1,
        }

client = OpenRouterClient()