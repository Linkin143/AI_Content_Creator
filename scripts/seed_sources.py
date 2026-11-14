"""Re-seed the source registry from app/research/sources_seed.py (idempotent).

Usage:
    python scripts/seed_sources.py
"""

import asyncio

from app.database.migrations import create_db_and_tables, seed_initial_data


async def main() -> None:
    await create_db_and_tables()
    result = await seed_initial_data()
    print(f"Seeded {result['sources_added']} new sources.")


if __name__ == "__main__":
    asyncio.run(main())
