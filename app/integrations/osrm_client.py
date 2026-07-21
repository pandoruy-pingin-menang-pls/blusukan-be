from typing import Any, Dict, List, Tuple

import httpx

from app.core.config import settings
from app.core.logging import logger


class OSRMClient:
    def __init__(self):
        self.base_url = settings.OSRM_BASE_URL.rstrip('/')
        # Gunakan profil jalan kaki (foot)
        self.profile = "foot"

    async def get_route(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Meminta rute jalan kaki dari OSRM.
        :param coordinates: List dari tuple (longitude, latitude) dalam urutan waypoint.
        :return: Dict berisi total distance (meter), estimated duration (menit), dan route GeoJSON.
        """
        if len(coordinates) < 2:
            raise ValueError("Minimal 2 koordinat (asal dan tujuan) dibutuhkan untuk routing OSRM.")

        # Format: lon,lat;lon,lat;...
        coord_string = ";".join([f"{lon},{lat}" for lon, lat in coordinates])

        # Endpoint: /route/v1/{profile}/{coordinates}
        # Parameter: geometries=geojson agar langsung dapat format standard GeoJSON LineString
        url = f"{self.base_url}/route/v1/{self.profile}/{coord_string}?geometries=geojson&overview=full"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                if data.get("code") != "Ok":
                    logger.error(f"OSRM returned non-Ok code: {data}")
                    raise Exception(f"OSRM Error: {data.get('message', 'Unknown')}")

                route = data["routes"][0]

                # Jarak dalam meter
                distance_m = route["distance"]
                # Durasi asli OSRM dalam detik, kita konversi ke menit
                duration_min = round(route["duration"] / 60)
                # Geometry dalam bentuk GeoJSON LineString
                geometry_geojson = route["geometry"]

                return {
                    "distance_meters": distance_m,
                    "duration_minutes": duration_min,
                    "route_geojson": geometry_geojson
                }

        except httpx.RequestError as e:
            logger.error(f"OSRM request failed: {str(e)}")
            # Fallback jika OSRM mati (berguna untuk mode dev/testing tanpa docker)
            return self._mock_route(coordinates)
        except Exception as e:
            logger.error(f"Error parsing OSRM response: {str(e)}")
            return self._mock_route(coordinates)

    def _mock_route(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Fallback mock jika server OSRM mati."""
        logger.warning("Returning MOCK OSRM Route.")
        return {
            "distance_meters": 1500,
            "duration_minutes": 25,
            "route_geojson": {
                "type": "LineString",
                "coordinates": [list(c) for c in coordinates]
            }
        }

osrm_client = OSRMClient()
