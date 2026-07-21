import asyncio
import json
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.session import async_session_maker
from app.integrations.gemini_client import gemini_client
from app.integrations.weather_client import weather_client
from app.modules.auth.models import User  # Fixed: Import User to resolve SQLAlchemy mapper
from app.modules.events.models import Event, EventStatus
from app.modules.inventory.calculator import (
    calculate_m_event,
    calculate_m_weather,
    calculate_predicted_stock,
)
from app.modules.inventory.models import InventoryRecommendation
from app.modules.merchant.models import Merchant


async def process_merchant_stock(db: AsyncSession, merchant: Merchant, events: list, weather_condition: str):
    """
    Menghitung rekomendasi stok untuk satu merchant.
    """
    if not merchant.baseline_inventory:
        return # Skip jika merchant tidak pernah isi baseline

    # 1. Hitung M_event
    # Format event dict untuk calculator: {"distance_m": val, "estimated_attendee_count": val}
    event_dicts = []
    nearby_events_json = []

    for event, distance_m in events:
        event_dicts.append({
            "distance_m": distance_m,
            "estimated_attendee_count": event.estimated_attendee_count
        })
        nearby_events_json.append({
            "id": str(event.id),
            "name": event.name,
            "distance_m": distance_m
        })

    m_event = calculate_m_event(event_dicts)

    # 2. Hitung M_weather
    m_weather = calculate_m_weather(weather_condition, merchant.category)

    # 3. Hitung predicted stock
    recommended_stock = {}
    for cat, baseline in merchant.baseline_inventory.items():
        predicted = calculate_predicted_stock(baseline, m_event, m_weather)
        recommended_stock[cat] = predicted

    # 4. Generate NLG dari Gemini
    prompt = f"""
    Kamu adalah "Mblus", asisten AI dari aplikasi Blusukan.
    Sapa pengguna dengan sebutan "Juragan" atau "Juragan Mblus".
    Toko mereka bernama {merchant.name} (kategori: {merchant.category}).

    Kondisi saat ini:
    - Cuaca: {weather_condition}
    - Event keramaian terdekat: Ada {len(event_dicts)} event.

    Rekomendasi stok jualan (Kategori -> Porsi/Item):
    {json.dumps(recommended_stock)}

    Tugasmu:
    1. Berikan pesan semangat yang to the point dan profesional tapi ramah (jangan lebay/berlebihan).
    2. Hubungkan saranmu dengan kondisi cuaca atau event hari ini.
    3. DILARANG KERAS menggunakan emoji apapun.
    4. Tampilkan rekomendasi stok dalam bentuk **bullet points** (titik/poin).
    5. Maksimal 2-3 kalimat pengantar saja sebelum menampilkan bullet points.
    6. Gunakan awalan kalimat "Mblus [kata kerja]..." atau variasinya sebelum memberikan list stok.
    7. Akhiri dengan satu kalimat singkat penyemangat yang profesional (misal: "Tetap semangat berdagang hari ini!").
    """

    ai_text = "Sistem AI sedang sibuk. Silakan gunakan angka yang tertera sebagai acuan."
    try:
        response = gemini_client.client.models.generate_content(
            model=settings.GEMINI_MODEL_TEXT,
            contents=prompt
        )
        if response.text:
            ai_text = response.text.strip()
    except Exception as e:
        logger.error(f"Failed to generate NLG for merchant {merchant.id}: {e}")

    # 5. Upsert ke database
    today = datetime.now(timezone.utc).date()

    stmt = insert(InventoryRecommendation).values(
        merchant_id=merchant.id,
        generated_for_date=today,
        weather_condition=weather_condition or "Unknown",
        nearby_events=nearby_events_json,
        recommended_stock=recommended_stock,
        ai_suggestion_text=ai_text
    )

    # On conflict update
    update_dict = {
        "weather_condition": stmt.excluded.weather_condition,
        "nearby_events": stmt.excluded.nearby_events,
        "recommended_stock": stmt.excluded.recommended_stock,
        "ai_suggestion_text": stmt.excluded.ai_suggestion_text
    }

    stmt = stmt.on_conflict_do_update(
        constraint="uq_merchant_date_inventory",
        set_=update_dict
    )

    await db.execute(stmt)

async def _calculate_daily_stock_async():
    """
    Main loop async untuk menghitung daily stock.
    """
    async with async_session_maker() as db:
        # Ambil semua merchant aktif
        result = await db.execute(select(Merchant).where(Merchant.is_active.is_(True)))
        merchants = result.scalars().all()

        if not merchants:
            logger.info("No active merchants found for stock recalc.")
            return

        semaphore = asyncio.Semaphore(10) # Maksimal 10 request AI bersamaan

        async def bounded_process(merchant):
            async with semaphore:
                try:
                    # Ambil cuaca (bisa di cache, tapi untuk simpel query aja per merchant location)
                    # Karena lokasi merchant beda-beda, kita get dari lon/lat
                    # Note: Merchant.location is geometry. We need lon/lat
                    # We can use func.ST_X and func.ST_Y
                    # Wait, func.ST_X(Merchant.location) might need cast to geometry if it's geography
                    # We can just get it from the merchant directly if we query it with the merchant
                    # But we already have the merchant object. We'll do a quick query.
                    loc_res = await db.execute(
                        select(func.ST_X(Merchant.location), func.ST_Y(Merchant.location))
                        .where(Merchant.id == merchant.id)
                    )
                    row = loc_res.first()
                    if row:
                        lon, lat = row
                    else:
                        lon, lat = 106.82, -6.20 # Fallback Jakarta

                    weather = await weather_client.get_current_weather(lat, lon)
                    weather = weather or "Clear" # Fallback

                    # Cari event terdekat (dalam 5km)
                    today = datetime.now(timezone.utc).date()
                    events_stmt = (
                        select(Event, func.ST_Distance(merchant.location, Event.location).label("distance_m"))
                        .where(Event.status == EventStatus.APPROVED)
                        .where(func.date(Event.start_datetime) == today)
                        .where(func.ST_DWithin(merchant.location, Event.location, 5000))
                    )
                    events_res = await db.execute(events_stmt)
                    events = events_res.all() # list of (Event, distance_m)

                    await process_merchant_stock(db, merchant, events, weather)
                except Exception as e:
                    logger.error(f"Error processing stock for merchant {merchant.id}: {e}")

        tasks = [bounded_process(m) for m in merchants]
        await asyncio.gather(*tasks)

        await db.commit()
        logger.info(f"Successfully processed stock predictions for {len(merchants)} merchants.")

@shared_task(name="app.workers.tasks_stock_recalc.calculate_daily_stock")
def calculate_daily_stock():
    """
    Entrypoint celery task.
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_calculate_daily_stock_async())
