from typing import Any, Dict, List

from app.core import constants


def calculate_m_event(events: List[Dict[str, Any]]) -> float:
    """
    Hitung multiplier berdasarkan events terdekat.
    Setiap event memberikan efek berdasarkan attendee dan distance.
    Max total m_event adalah 1.0 (100% surge).
    """
    total_m = 0.0
    for event in events:
        distance = event.get("distance_m", 9999)
        attendees = event.get("estimated_attendee_count", 0)

        # High impact
        if attendees >= constants.EVENT_ATTENDEE_HIGH and distance <= constants.EVENT_DISTANCE_CLOSE_M:
            total_m += constants.M_EVENT_HIGH_IMPACT
        # Low impact
        elif attendees >= constants.EVENT_ATTENDEE_LOW and distance <= constants.EVENT_DISTANCE_FAR_M:
            total_m += constants.M_EVENT_LOW_IMPACT

    return min(total_m, 1.0)

def calculate_m_weather(weather_condition: str, category: str) -> float:
    """
    Hitung multiplier berdasarkan cuaca dan kategori jualan.
    """
    weather = weather_condition.lower() if weather_condition else ""
    cat = category.lower() if category else ""

    if weather in ["rain", "thunderstorm", "drizzle"]:
        if "hot" in cat or "hangat" in cat or "makanan" in cat:
            return constants.M_WEATHER_RAIN_HOT_CULINARY
        if "cold" in cat or "es" in cat or "minuman dingin" in cat:
            return constants.M_WEATHER_RAIN_COLD_BEVERAGE
        if "retail" in cat or "kerajinan" in cat or "baju" in cat:
            return constants.M_WEATHER_RAIN_RETAIL

    if weather in ["clear", "sunny"]:
        if "cold" in cat or "es" in cat or "minuman dingin" in cat:
            return constants.M_WEATHER_SUNNY_COLD_BEVERAGE

    return 0.0

def calculate_predicted_stock(baseline: int, m_event: float, m_weather: float) -> int:
    """
    Formula: S_predicted = S_baseline * (1 + m_event + m_weather)
    Nilai tidak boleh kurang dari 0 (clamp >= 0).
    """
    if baseline < 0:
        return 0

    predicted = int(baseline * (1.0 + m_event + m_weather))
    return max(0, predicted)
