"""
LIHA FOOD VISION - Core Analysis Pipeline
Identifies foods, estimates portions, parses nutrition labels/OCR, multi-food detection, and nutrition estimation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("liha_food_vision")

def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"
MODEL_NAME = "models/gemini-3.8-flash"

def _load_gemini_key() -> str:
    try:
        if API_KEY_PATH.exists():
            with open(API_KEY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("gemini_api_key", "").strip()
    except Exception as e:
        logger.error(f"Failed to load Gemini key: {e}")
    return ""

FOOD_VISION_SYSTEM_PROMPT = """You are LIHA Food Vision — an expert AI food, nutrition, and OCR analysis engine.
Your task is to analyze food images (fresh, cooked, or packaged) and return structured JSON analysis.

CRITICAL INSTRUCTIONS:
1. Identify all visible foods accurately.
2. If packaged food with a nutrition label is visible, perform OCR and set is_packaged=true and source="LABEL DATA".
3. If unlabelled/fresh/cooked food, set is_packaged=false and source="ESTIMATED".
4. Estimate portions realistically based on visual cues.
5. Provide detailed nutrition breakdown per serving (Calories, Protein, Carbohydrates, Total Fat, Saturated Fat, Fibre, Sugar, Sodium, Key Nutrients).
6. Classify category (Fruit, Vegetable, Grain, Protein food, Dairy, Snack, Dessert, Beverage, Processed food, Fast food, Other).
7. Provide an objective, non-judgmental nutritional summary and personalized response options.
8. NEVER claim estimated numbers are 100% exact. Always mark estimation status clearly.

RETURN ONLY VALID JSON WITH THIS STRICT SCHEMA:
{
  "is_packaged": false,
  "data_source": "ESTIMATED",
  "confidence": "HIGH",
  "meal_type": "SINGLE",
  "detected_items": [
    {
      "name": "Banana",
      "category": "Fruit",
      "portion": "1 medium banana (~118g)",
      "nutrition": {
        "calories": "105 kcal",
        "protein": "1.3 g",
        "carbohydrates": "27 g",
        "fat": "0.4 g",
        "saturated_fat": "0.1 g",
        "fibre": "3.1 g",
        "sugar": "14 g",
        "sodium": "1 mg"
      },
      "key_nutrients": ["Potassium", "Vitamin B6", "Vitamin C"],
      "analysis": "This appears to be a nutrient-dense food providing fibre and essential vitamins."
    }
  ],
  "overall_summary": {
    "title": "Banana",
    "total_calories": "105 kcal",
    "total_protein": "1.3 g",
    "total_carbs": "27 g",
    "total_fat": "0.4 g",
    "total_fibre": "3.1 g",
    "overall_notes": "Single item detected. Rich in potassium and natural energy."
  },
  "voice_text": "I identified this as a banana. The nutrition values shown here are estimates based on the visible portion.",
  "label_details": {
    "ingredients": [],
    "allergens": [],
    "serving_size_label": ""
  }
}
"""

def analyze_food_image(image_b64: str, mime: str = "image/jpeg") -> Dict[str, Any]:
    key = _load_gemini_key()
    if key:
        genai.configure(api_key=key)

    try:
        model = genai.GenerativeModel(
            MODEL_NAME,
            system_instruction=FOOD_VISION_SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json"
            }
        )
        response = model.generate_content([
            {"mime_type": mime, "data": image_b64},
            "Analyze this food image comprehensively following the LIHA Food Vision format."
        ])
        
        raw = response.text.strip()
        data = json.loads(raw)
        return data

    except Exception as e:
        logger.error(f"Food Vision analysis failed: {e}")
        return {
            "error": True,
            "message": f"I couldn't confidently identify the food from this image. Please provide a clearer photo. ({e})",
            "voice_text": "I could not confidently identify the food from this image. Please try again with a clearer photo."
        }

def analyze_food_file(file_path: str) -> Dict[str, Any]:
    import base64
    path = Path(file_path)
    if not path.exists():
        return {"error": True, "message": "File not found.", "voice_text": "Selected image file was not found."}

    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp"
    }
    mime = mime_map.get(path.suffix.lower(), "image/jpeg")

    with open(path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    return analyze_food_image(img_b64, mime)
