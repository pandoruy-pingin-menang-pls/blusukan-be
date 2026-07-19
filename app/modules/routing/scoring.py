from app.core.constants import MAX_REVIEW_THRESHOLD

# ================================================================
# ENGINEERING DECISION LOG - Wajib dipertahankan untuk referensi juri
# ================================================================
# 1. Term Distance: Implementasi w3 menggunakan Distance_normalized (Opsi A)
#    BUKAN 1/Distance secara literal seperti di proposal awal.
#    Alasan: Jika 1/Distance_normalized dipakai literal, merchant paling jauh
#    (Distance_norm -> 0) akan menghasilkan score -> Tak Terhingga (berlawanan tujuan).
#    Opsi A (Distance Normalized murni) konsisten dengan definisi algoritma SAW.
# 2. Bobot w1-w4: rule-based lookup table (weight_presets.py)
#    Digunakan untuk Hackathon MVP agar deterministik, cepat, dan mudah di-unit test.
# 3. HiddenGemIndex = 1 - min(review_count / MAX_REVIEW_THRESHOLD, 1)
#    MAX_REVIEW_THRESHOLD diatur di constants.py (Default: 100).
# ================================================================


def calculate_hidden_gem_index(review_count: int, max_threshold: int = MAX_REVIEW_THRESHOLD) -> float:
    """
    Menghitung seberapa 'Hidden Gem' suatu tempat.
    Semakin sedikit review, semakin mendekati 1.0.
    Jika review sudah melewati max_threshold, nilainya 0.0.
    """
    return 1.0 - min(review_count / float(max_threshold), 1.0)


def calculate_distance_norm(distance_m: float, max_radius_m: float) -> float:
    """
    Menormalkan jarak ke dalam rentang [0, 1].
    Jarak 0 (Sangat dekat) -> Score 1.0
    Jarak >= max_radius_m -> Score 0.0
    """
    if max_radius_m <= 0:
        return 0.0
    return max(1.0 - (distance_m / float(max_radius_m)), 0.0)


def calculate_rating_norm(rating: float) -> float:
    """
    Menormalkan rating (0-5) menjadi [0, 1].
    """
    return rating / 5.0


def calculate_saw_score(
    hidden_gem_index: float,
    category_match: float,
    distance_norm: float,
    rating_norm: float,
    weights: dict,
    is_redemption_partner: bool
) -> float:
    """
    Kalkulasi akhir algoritma Simple Additive Weighting (SAW).
    Ditambah dengan bonus multiplier untuk Redemption Partner (C).
    """
    # Pastikan weights berisi w1, w2, w3, w4
    w1 = weights.get("w1", 0.0)
    w2 = weights.get("w2", 0.0)
    w3 = weights.get("w3", 0.0)
    w4 = weights.get("w4", 0.0)

    score = (
        (w1 * hidden_gem_index) +
        (w2 * category_match) +
        (w3 * distance_norm) +
        (w4 * rating_norm)
    )

    # Bonus multiplier C = 1.2 jika dia adalah merchant langganan event (redemption partner)
    # Sesuai proposal: Score = Score * C
    c_multiplier = 1.2 if is_redemption_partner else 1.0

    final_score = score * c_multiplier

    return round(final_score, 4)
