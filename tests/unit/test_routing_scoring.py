import pytest

from app.modules.routing.scoring import (
    calculate_distance_norm,
    calculate_hidden_gem_index,
    calculate_rating_norm,
    calculate_saw_score,
)
from app.modules.routing.weight_presets import get_weights


def test_weight_presets_normalization():
    """
    Memastikan total dari w1 + w2 + w3 + w4 selalu 1.0 (setelah pembulatan).
    """
    test_cases = [
        {"avoid_crowds": False, "interest_categories": "bebas"},
        {"avoid_crowds": True, "interest_categories": "makanan pedas"},
        {"avoid_crowds": False, "interest_categories": "batik tulis"},
        {"avoid_crowds": False, "interest_categories": "terserah"}, # akan di-parse jadi "bebas" di gemini
        {} # empty dict fallback
    ]

    for case in test_cases:
        weights = get_weights(case)
        total = weights["w1"] + weights["w2"] + weights["w3"] + weights["w4"]
        # Akurasi float python
        assert pytest.approx(total, 0.001) == 1.0

def test_weight_presets_logic():
    """
    Memastikan logika prioritas bobot berjalan benar.
    """
    # Kasus 1: avoid_crowds = True -> w1 (Hidden Gem) harus paling tinggi
    w_avoid = get_weights({"avoid_crowds": True, "interest_categories": "bebas"})
    assert w_avoid["w1"] > w_avoid["w2"]
    assert w_avoid["w1"] == 0.50

    # Kasus 2: spesifik kategori -> w2 (Category) harus paling tinggi
    w_cat = get_weights({"avoid_crowds": False, "interest_categories": "kopi lokal"})
    assert w_cat["w2"] > w_cat["w1"]
    assert w_cat["w2"] == 0.60

    # Kasus 3: bebas -> w3 (Jarak) dan w4 (Rating) harus lebih tinggi dari w2
    w_bebas = get_weights({"avoid_crowds": False, "interest_categories": "bebas"})
    assert w_bebas["w3"] > w_bebas["w2"]
    assert w_bebas["w4"] > w_bebas["w2"]


def test_calculate_hidden_gem_index():
    """
    Semakin sedikit review, nilainya harus semakin dekat ke 1.0.
    Jika review melebihi threshold, nilainya 0.
    """
    idx_0 = calculate_hidden_gem_index(0, max_threshold=100)
    assert idx_0 == 1.0

    idx_50 = calculate_hidden_gem_index(50, max_threshold=100)
    assert idx_50 == 0.5

    idx_150 = calculate_hidden_gem_index(150, max_threshold=100)
    assert idx_150 == 0.0

def test_calculate_distance_norm():
    """
    Jarak dekat -> score mendekati 1.
    Jarak melebihi max_radius -> score 0.
    """
    norm_0 = calculate_distance_norm(0, max_radius_m=1000)
    assert norm_0 == 1.0

    norm_500 = calculate_distance_norm(500, max_radius_m=1000)
    assert norm_500 == 0.5

    norm_1500 = calculate_distance_norm(1500, max_radius_m=1000)
    assert norm_1500 == 0.0

def test_calculate_rating_norm():
    assert calculate_rating_norm(5.0) == 1.0
    assert calculate_rating_norm(2.5) == 0.5
    assert calculate_rating_norm(0.0) == 0.0

def test_calculate_saw_score():
    """
    Test algoritma utama SAW beserta bonus multiplier C.
    """
    weights = {"w1": 0.25, "w2": 0.25, "w3": 0.25, "w4": 0.25}

    # Kasus sempurna (semua parameter mentok max)
    score_perfect = calculate_saw_score(
        hidden_gem_index=1.0,
        category_match=1.0,
        distance_norm=1.0,
        rating_norm=1.0,
        weights=weights,
        is_redemption_partner=False
    )
    assert score_perfect == 1.0

    # Kasus partner event (harus ada multiplier 1.2)
    score_partner = calculate_saw_score(
        hidden_gem_index=1.0,
        category_match=1.0,
        distance_norm=1.0,
        rating_norm=1.0,
        weights=weights,
        is_redemption_partner=True
    )
    assert score_partner == 1.2

    # Kasus terburuk
    score_worst = calculate_saw_score(
        hidden_gem_index=0.0,
        category_match=0.0,
        distance_norm=0.0,
        rating_norm=0.0,
        weights=weights,
        is_redemption_partner=False
    )
    assert score_worst == 0.0
