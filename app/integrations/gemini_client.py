import json
from typing import Any, Dict, List

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.constants import (
    DEFAULT_BUDGET_IDR,
    DEFAULT_SEARCH_RADIUS_METER,
    DEFAULT_TIME_LIMIT_MINUTES,
)
from app.core.logging import logger


class GeminiClient:
    def __init__(self):
        # We handle cases where GEMINI_API_KEY might be empty in local dev
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY is not set. AI functions will return mocked data.")

    async def extract_menu_from_image(self, file_bytes: bytes, mime_type: str = "image/jpeg") -> List[Dict[str, Any]]:
        """
        Extract menu items from an image and return them as a strict JSON array.
        """
        if not self.client:
            logger.info("Mocking Gemini response for extract_menu_from_image")
            return [
                {"item_name": "Nasi Goreng Spesial (MOCK)", "price": 15000, "category": "culinary"},
                {"item_name": "Es Teh Manis (MOCK)", "price": 3000, "category": "cold_beverage"}
            ]

        prompt = """
        Anda adalah asisten data entry. Tugas Anda adalah membaca foto menu rumah makan ini.
        Hasilkan output HANYA DALAM FORMAT JSON berupa array of objects.
        Setiap object wajib memiliki keys:
        - "item_name" (string): Nama menu.
        - "price" (number atau null): Harga menu dalam angka tanpa simbol mata uang. Jika harga tidak ada/tidak terbaca, isikan null.
        - "category" (string): Kategori menu. Pilih salah satu dari: culinary, hot_culinary, cold_beverage, cold_beverage_dessert, craft, batik, outdoor_retail. Jika tidak yakin, pilih culinary.

        Jangan mengarang menu yang tidak ada di foto. Jangan beri teks penjelasan apapun selain JSON array.
        """

        try:
            # Note: We are using synchronous call here for simplicity, but in production we should use async
            # if supported by google-genai, or run in a threadpool.
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_VISION,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                ]
            )

            raw_text = response.text
            # Defensively clean markdown formatting if Gemini included it (e.g., ```json ... ```)
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]

            return json.loads(clean_text.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON output: {e}. Raw output: {raw_text}")
            # We return empty array so it doesn't crash the server (Draft items will just be empty)
            return []
        except Exception as e:
            logger.error(f"Gemini API error during extract_menu_from_image: {str(e)}")
            raise

    async def parse_constraints(self, raw_query: str) -> dict:
        """
        Extract constraints from a natural language query for itinerary generation.
        Returns a dictionary with parsed constraints.
        """
        if not self.client:
            logger.info("Mocking Gemini response for parse_constraints")
            return {
                "time_limit_minutes": DEFAULT_TIME_LIMIT_MINUTES,
                "budget_idr": DEFAULT_BUDGET_IDR,
                "search_radius_meter": DEFAULT_SEARCH_RADIUS_METER,
                "interest_categories": "kuliner, budaya",
                "avoid_crowds": False
            }

        prompt = f"""
        Anda adalah asisten pariwisata ahli. Tugas Anda adalah mengekstrak parameter batasan (constraints) dari permintaan turis berikut ini.
        Permintaan: "{raw_query}"

        Hasilkan output HANYA DALAM FORMAT JSON berupa satu object.
        Object wajib memiliki keys berikut. Jika tidak disebutkan di permintaan, gunakan logika/asumsi standar (default) yang wajar:
        - "time_limit_minutes" (integer): Batas waktu jalan-jalan dalam menit. (Default wajar: {DEFAULT_TIME_LIMIT_MINUTES}).
        - "budget_idr" (integer): Total budget dalam Rupiah. (Default wajar: {DEFAULT_BUDGET_IDR}).
        - "search_radius_meter" (integer): Radius pencarian dari titik awal dalam meter. (Default wajar: {DEFAULT_SEARCH_RADIUS_METER}).
        - "interest_categories" (string): Kategori minat yang dicari (misal: "makanan pedas, kerajinan lokal"). Jika turis menyatakan "terserah", "apa aja", "bebas", atau tidak menyebutkan kategori secara spesifik, maka WAJIB isi persis dengan kata: "bebas".
        - "avoid_crowds" (boolean): True jika turis spesifik ingin menghindari keramaian (hidden gems), False jika bebas. (Default: false).

        Jangan beri teks penjelasan apapun selain JSON object.
        """

        try:
            response = self.client.models.generate_content(
                model=settings.GEMINI_MODEL_TEXT,
                contents=prompt
            )

            raw_text = response.text
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]

            parsed = json.loads(clean_text.strip())

            # Sanitasi fallback ringan jika gemini lalai
            parsed.setdefault("time_limit_minutes", DEFAULT_TIME_LIMIT_MINUTES)
            parsed.setdefault("budget_idr", DEFAULT_BUDGET_IDR)
            parsed.setdefault("search_radius_meter", DEFAULT_SEARCH_RADIUS_METER)
            parsed.setdefault("interest_categories", "bebas")
            parsed.setdefault("avoid_crowds", False)

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON output in parse_constraints: {e}. Raw output: {raw_text}")
            return {
                "time_limit_minutes": DEFAULT_TIME_LIMIT_MINUTES,
                "budget_idr": DEFAULT_BUDGET_IDR,
                "search_radius_meter": DEFAULT_SEARCH_RADIUS_METER,
                "interest_categories": "bebas",
                "avoid_crowds": False
            }
        except Exception as e:
            logger.error(f"Gemini API error during parse_constraints: {str(e)}")
            raise

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate 768-dimensional vector embedding for the given text.
        """
        if not self.client:
            logger.info("Mocking Gemini response for embed_text")
            # Return a zero vector for mock
            return [0.0] * 768

        try:
            response = self.client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Gemini API error during embed_text: {str(e)}")
            raise

gemini_client = GeminiClient()
