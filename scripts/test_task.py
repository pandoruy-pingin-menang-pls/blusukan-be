import asyncio

from app.workers.tasks_stock_recalc import _calculate_daily_stock_async

if __name__ == "__main__":
    asyncio.run(_calculate_daily_stock_async())
