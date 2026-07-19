from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class WeatherClient:
    def __init__(self):
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.api_key = settings.WEATHER_API_KEY

    async def get_current_weather(self, lat: float, lon: float) -> Optional[str]:
        """
        Mengambil kondisi cuaca saat ini dari OpenWeatherMap berdasarkan lat/lon.
        Mengembalikan string kondisi utama (misal: 'Rain', 'Clear', 'Clouds').
        Jika gagal, mengembalikan None (fallback).
        """
        if not self.api_key:
            logger.warning("WEATHER_API_KEY is missing. Skipping weather check.")
            return None

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()

                weather_array = data.get("weather", [])
                if weather_array:
                    # Mengembalikan 'main' (Rain, Snow, Extreme, Clear, Clouds)
                    return weather_array[0].get("main")
                return None
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in WeatherClient: {e}")
            return None

weather_client = WeatherClient()
