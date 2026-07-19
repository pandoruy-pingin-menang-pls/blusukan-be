from app.core.constants import (
    EVENT_ATTENDEE_HIGH,
    EVENT_ATTENDEE_LOW,
    EVENT_DISTANCE_CLOSE_M,
    EVENT_DISTANCE_FAR_M,
)
from app.modules.inventory.calculator import (
    calculate_m_event,
    calculate_m_weather,
    calculate_predicted_stock,
)


def test_m_event_high_impact():
    events = [
        {"distance_m": EVENT_DISTANCE_CLOSE_M - 100, "estimated_attendee_count": EVENT_ATTENDEE_HIGH + 1000} # 6000 attendees, 900m
    ]
    m_event = calculate_m_event(events)
    assert m_event == 0.30

def test_m_event_low_impact():
    events = [
        {"distance_m": EVENT_DISTANCE_FAR_M - 100, "estimated_attendee_count": EVENT_ATTENDEE_LOW + 2000} # 3000 attendees, 2900m
    ]
    m_event = calculate_m_event(events)
    assert m_event == 0.10

def test_m_event_multiple_clamp():
    events = [
        {"distance_m": 500, "estimated_attendee_count": 6000},
        {"distance_m": 500, "estimated_attendee_count": 6000},
        {"distance_m": 500, "estimated_attendee_count": 6000},
        {"distance_m": 500, "estimated_attendee_count": 6000}
    ] # 4 high impact = 1.20, clamped to 1.0
    m_event = calculate_m_event(events)
    assert m_event == 1.0

def test_m_weather_rain_extreme_minus_combo():
    # Cuaca hujan, kategori minuman es (extreme minus)
    m_weather = calculate_m_weather("Rain", "KULINER_DINGIN")
    assert m_weather == -0.20

    m_weather_retail = calculate_m_weather("Rain", "KERAJINAN")
    assert m_weather_retail == -0.30

def test_m_weather_sunny_plus_combo():
    # Cuaca cerah, kategori minuman es
    m_weather = calculate_m_weather("Sunny", "KULINER_DINGIN")
    assert m_weather == 0.25

def test_calculate_predicted_stock_clamp_to_zero():
    # Extreme minus combo
    # Baseline 10
    # m_event = 0
    # m_weather = -0.30 (Rain, Retail) -> 10 * (1 - 0.3) = 7
    predicted = calculate_predicted_stock(10, 0.0, -0.30)
    assert predicted == 7

    # What if it's very negative? Say, we tweak formula later or add another penalty
    predicted_negative = calculate_predicted_stock(10, -0.5, -0.6)
    assert predicted_negative == 0
