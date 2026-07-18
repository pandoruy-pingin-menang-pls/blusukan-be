"""
Semua konstanta baku dan magic numbers aplikasi didefinisikan di sini.
Ini bertindak sebagai Single Source of Truth agar mudah dilakukan tuning
tanpa harus mencari ke dalam service layer.
"""

# --- Routing & Itinerary Constants ---

# Fallback values jika user tidak memberikan input yang spesifik
DEFAULT_TIME_LIMIT_MINUTES = 300
DEFAULT_SEARCH_RADIUS_METER = 2000
DEFAULT_BUDGET_IDR = 999_999_999

# Clamp boundaries (batas minimal & maksimal yang diizinkan untuk keamanan server)
MIN_SEARCH_RADIUS_METER = 500
MAX_SEARCH_RADIUS_METER = 5000
MIN_BUDGET_IDR = 10_000

# Scoring Constants (SAW)
# Ambang batas review count sebelum merchant dianggap 'mainstream' (bukan hidden gem lagi)
MAX_REVIEW_THRESHOLD = 100

# --- Merchant & Catalog Constants ---
# Batasan jumlah unggah menu harian per merchant untuk mencegah abuse API Gemini
MAX_DAILY_INGEST = 5

# --- Predictive Stocking Constants ---
# Threshold Attendee (Jumlah pengunjung event)
EVENT_ATTENDEE_HIGH = 5000
EVENT_ATTENDEE_LOW = 1000

# Threshold Distance (Jarak event ke merchant)
EVENT_DISTANCE_CLOSE_M = 1000
EVENT_DISTANCE_FAR_M = 3000

# Surge Multipliers (M_event)
M_EVENT_HIGH_IMPACT = 0.30
M_EVENT_LOW_IMPACT = 0.10

# Weather Multipliers (M_weather)
M_WEATHER_RAIN_HOT_CULINARY = 0.15
M_WEATHER_RAIN_COLD_BEVERAGE = -0.20
M_WEATHER_RAIN_RETAIL = -0.30
M_WEATHER_SUNNY_COLD_BEVERAGE = 0.25

# --- Gamification & Credit Score Constants ---
# Formula Kenaikan Level: Required XP = BASE_XP * (Level * LEVEL_MULTIPLIER)
GAMIFICATION_BASE_XP = 1000
GAMIFICATION_LEVEL_MULTIPLIER = 1.5

# Bobot Credit Scoring (Total = 1.0)
CREDIT_SCORE_WEIGHT_FREQ = 0.40
CREDIT_SCORE_WEIGHT_REVENUE = 0.30
CREDIT_SCORE_WEIGHT_PREDICTION = 0.20
CREDIT_SCORE_WEIGHT_RATING = 0.10

