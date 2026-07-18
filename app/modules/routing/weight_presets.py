"""
Rule-based lookup table untuk bobot (weights) SAW Scoring.
Ini memetakan hasil parsing NLP Gemini (parsed_constraints) menjadi bobot matematis yang pasti.
"""

def get_weights(parsed_constraints: dict) -> dict:
    """
    Mengembalikan bobot yang sudah dinormalisasi (total = 1.0)
    berdasarkan preferensi user.
    w1 = Bobot Hidden Gem (Berdasarkan parameter avoid_crowds)
    w2 = Bobot Kecocokan Kategori (Berdasarkan interest_categories)
    w3 = Bobot Jarak (Distance)
    w4 = Bobot Rating
    """
    
    # 1. Base weights (Asumsi standar jika user tidak spesifik)
    w1_base = 0.20
    w2_base = 0.30
    w3_base = 0.30
    w4_base = 0.20
    
    # 2. Adjustments berdasarkan constraints
    avoid_crowds = parsed_constraints.get("avoid_crowds", False)
    interest_categories = parsed_constraints.get("interest_categories", "bebas").lower()
    
    if avoid_crowds:
        # Jika user spesifik minta menghindari keramaian, Hidden Gem menjadi prioritas absolut
        w1_base = 0.50
        w2_base = 0.20
        w3_base = 0.15
        w4_base = 0.15
        
    elif interest_categories == "bebas":
        # Jika user bilang "terserah", turunkan prioritas kategori, 
        # naikkan prioritas Jarak dan Rating (cari yang paling dekat & paling enak/bagus)
        w1_base = 0.20
        w2_base = 0.05
        w3_base = 0.40
        w4_base = 0.35
        
    else:
        # Jika user sangat spesifik mencari barang/kategori tertentu (tapi tidak anti keramaian)
        w1_base = 0.10
        w2_base = 0.60
        w3_base = 0.15
        w4_base = 0.15

    # 3. Normalisasi (Memastikan total w1+w2+w3+w4 = 1.0)
    total = w1_base + w2_base + w3_base + w4_base
    
    return {
        "w1": round(w1_base / total, 3),
        "w2": round(w2_base / total, 3),
        "w3": round(w3_base / total, 3),
        "w4": round(w4_base / total, 3),
    }
