from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    DEFAULT_BUDGET_IDR,
    DEFAULT_SEARCH_RADIUS_METER,
    DEFAULT_TIME_LIMIT_MINUTES,
    MAX_SEARCH_RADIUS_METER,
    MIN_BUDGET_IDR,
    MIN_SEARCH_RADIUS_METER,
)
from app.core.exceptions import RoutingNoMerchantsException
from app.core.logging import logger
from app.integrations.gemini_client import gemini_client
from app.integrations.osrm_client import osrm_client
from app.modules.catalog.models import MerchantCatalogItem
from app.modules.merchant.models import Merchant
from app.modules.routing.models import Itinerary
from app.modules.routing.scoring import (
    calculate_distance_norm,
    calculate_hidden_gem_index,
    calculate_rating_norm,
    calculate_saw_score,
)
from app.modules.routing.weight_presets import get_weights


class RoutingService:
    @staticmethod
    async def generate_itinerary(
        db: AsyncSession,
        user_id: UUID,
        raw_query: str,
        current_lat: float,
        current_lon: float
    ) -> Itinerary:
        """
        Orkestrator utama Dolan Mode:
        1. Ekstrak constraint via Gemini NLP.
        2. Tentukan jumlah destinasi & budget per destinasi.
        3. Query spasial (ST_DWithin) + Vector Search jika ada kategori.
        4. Kalkulasi score SAW per merchant.
        5. Sorting & ambil top N.
        6. Panggil OSRM untuk routing GeoJSON.
        7. Simpan ke database dan return.
        """

        # 1. NLP Parse Constraints
        logger.info(f"Generating itinerary for user {user_id}: {raw_query}")
        parsed_constraints = await gemini_client.parse_constraints(raw_query)

        time_limit = parsed_constraints.get("time_limit_minutes", DEFAULT_TIME_LIMIT_MINUTES)
        budget = parsed_constraints.get("budget_idr", DEFAULT_BUDGET_IDR)
        radius = parsed_constraints.get("search_radius_meter", DEFAULT_SEARCH_RADIUS_METER)
        interest = parsed_constraints.get("interest_categories", "bebas")

        # Clamp radius untuk keamanan DB
        radius = min(max(radius, MIN_SEARCH_RADIUS_METER), MAX_SEARCH_RADIUS_METER)

        # Clamp budget (minimal sesuai konstanta agar tidak Rp0)
        budget = max(budget, MIN_BUDGET_IDR)

        # 2. Heuristik Waktu & Budget
        # Asumsi 1 tempat butuh waktu 60 menit (termasuk jalan + makan/belanja)
        target_merchant_count = max(1, min(time_limit // 60, 4)) # Maksimal 4 toko

        # Dapatkan bobot SAW
        weights = get_weights(parsed_constraints)

        # Persiapkan titik awal
        origin_pt = f"SRID=4326;POINT({current_lon} {current_lat})"

        # 3. Query Database
        # 3. Vector Embedding (jika ada kategori spesifik)
        query_embeddings = []
        if interest and interest.lower() != "bebas":
            import re
            # Pisahkan query ganda (contoh: "kerajinan dan makanan") jadi ["kerajinan", "makanan"]
            categories = [c.strip() for c in re.split(r',|\bdan\b|\batau\b|\b&\b', interest.lower()) if c.strip()]
            try:
                for cat in categories:
                    emb = await gemini_client.embed_text(cat)
                    query_embeddings.append(emb)
            except Exception as e:
                logger.error(f"Failed to generate embedding for {interest}: {e}")
                # Berikan warning ke user bahwa pencarian dialihkan ke "bebas" karena Rate Limit AI
                parsed_constraints["warning"] = "Sistem AI sedang mencapai batas *Rate Limit*. Pencarian otomatis dialihkan ke mode default. Silakan coba 1 menit lagi untuk pencarian spesifik."

        # Base query: Cari merchant di dalam radius
        # ST_DWithin dalam meter (karena SRID 4326, kita cast ke geography)
        stmt = (
            select(
                Merchant,
                func.ST_Distance(
                    cast(Merchant.location, Geography(srid=4326)),
                    func.ST_GeographyFromText(origin_pt)
                ).label("distance_m"),
                func.ST_X(Merchant.location).label("lon"),
                func.ST_Y(Merchant.location).label("lat")
            )
            .where(
                func.ST_DWithin(
                    cast(Merchant.location, Geography(srid=4326)),
                    func.ST_GeographyFromText(origin_pt),
                    radius
                )
            )
            .where(Merchant.is_active)
        )

        result = await db.execute(stmt)
        merchants_data = result.all() # Tuple (Merchant, distance_m, lon, lat)

        if not merchants_data:
            raise RoutingNoMerchantsException(radius=radius)

        # Ambil category match if needed
        merchant_category_scores = {}
        if query_embeddings:
            # Cari distance minimum (closest) untuk item yang dimiliki merchant-merchant ini
            merchant_ids = [row[0].id for row in merchants_data]

            # Buat array of distance untuk masing-masing embedding query
            distances = []
            for emb in query_embeddings:
                distances.append(MerchantCatalogItem.embedding.cosine_distance(emb))

            # Jika user cari > 1 kategori, ambil jarak TETERDEKAT (paling mirip) dari semua opsi tersebut (Logika OR)
            least_distance = distances[0] if len(distances) == 1 else func.least(*distances)

            vector_stmt = (
                select(
                    MerchantCatalogItem.merchant_id,
                    func.min(least_distance).label("min_distance")
                )
                .where(MerchantCatalogItem.merchant_id.in_(merchant_ids))
                .where(MerchantCatalogItem.embedding.is_not(None))
                .group_by(MerchantCatalogItem.merchant_id)
            )
            vec_res = await db.execute(vector_stmt)
            for row in vec_res:
                # Cosine distance rentang [0, 2]. Similarity = 1 - distance (asumsi distance [0,1])
                similarity = max(1.0 - row.min_distance, 0.0)
                merchant_category_scores[row.merchant_id] = similarity

        # 4. Kalkulasi Score SAW
        scored_merchants = []
        for m, dist_m, m_lon, m_lat in merchants_data:
            # a. Hidden Gem
            h_idx = calculate_hidden_gem_index(m.review_count)
            # b. Category Match
            # Jika ada query spesifik, merchant yg tidak punya menu akan mendapat skor 0.0 (dan akan di-filter out).
            c_match = merchant_category_scores.get(m.id, 0.0) if query_embeddings else 1.0

            # Hard filter: Threshold dikembalikan ke 0.55.
            # Berkat logika func.least (OR search), kategori ganda akan dinilai terpisah (vektor murni).
            # "Kerajinan" vs "Cilok" skornya ~0.54, jadi dengan threshold 0.55 toko makanan akan DIBLOKIR untuk "kerajinan".
            # "Makanan" vs "Cilok" skornya ~0.62, jadi akan LOLOS.
            if query_embeddings and c_match < 0.55:
                continue

            # c. Distance Norm
            d_norm = calculate_distance_norm(dist_m, radius)
            # d. Rating Norm
            r_norm = calculate_rating_norm(float(m.baseline_rating))

            score = calculate_saw_score(
                hidden_gem_index=h_idx,
                category_match=c_match,
                distance_norm=d_norm,
                rating_norm=r_norm,
                weights=weights,
                is_redemption_partner=m.is_redemption_partner
            )

            scored_merchants.append({
                "merchant": m,
                "score": score,
                "distance_m": dist_m,
                "lon": m_lon,
                "lat": m_lat
            })

        if not scored_merchants:
            # Jika setelah difilter kategori ternyata tidak ada yang relevan sama sekali
            raise RoutingNoMerchantsException(radius=radius)

        # 5. Sort DESC dan ambil top N
        scored_merchants.sort(key=lambda x: x["score"], reverse=True)
        top_merchants = scored_merchants[:target_merchant_count]

        if not top_merchants:
             raise RoutingNoMerchantsException(radius=radius)

        # 6. Panggil OSRM
        # Titik pertama adalah user (lon, lat)
        coords = [(current_lon, current_lat)]
        waypoints_json = []

        for idx, item in enumerate(top_merchants):
            m = item["merchant"]
            m_lon = item["lon"]
            m_lat = item["lat"]
            coords.append((m_lon, m_lat))

            waypoints_json.append({
                "merchant_id": str(m.id),
                "name": m.name,
                "lat": m_lat,
                "lon": m_lon,
                "score": item["score"],
                "order": idx + 1,
                "category": m.category or "Kuliner",
            })

        # Panggil OSRM
        try:
            route_data = await osrm_client.get_route(coords)
            route_geojson = route_data["route_geojson"]
            total_duration_minutes = route_data["duration_minutes"]
        except Exception as e:
            logger.error(f"OSRM Routing failed, fallback to mock: {e}")
            route_geojson = {"type": "LineString", "coordinates": coords}
            total_duration_minutes = len(coords) * 15 # mock 15 mnt per titik

        # 7. Simpan ke Database
        itinerary = Itinerary(
            user_id=user_id,
            raw_query=raw_query,
            parsed_constraints=parsed_constraints,
            waypoints=waypoints_json,
            route_geojson=route_geojson,
            estimated_duration_minutes=total_duration_minutes,
            status="active"
        )
        db.add(itinerary)
        await db.commit()
        await db.refresh(itinerary)

        return itinerary

routing_service = RoutingService()
