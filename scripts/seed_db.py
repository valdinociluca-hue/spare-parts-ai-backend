"""
scripts/seed_db.py — Development database seeder.

Creates test data in the local development database for:
  - Manual testing of the API without needing real Bitrix webhooks
  - Integration test fixtures
  - Frontend / admin UI development (when added)

NOT for production use. Guard with environment check.

TODO:
  - Add sample RequestLog records with various categories
  - Add corresponding ClassificationLog records
  - Add sample ProcessingEvent records
  - Add a --reset flag (DROP + recreate tables before seeding)
"""

import asyncio


async def seed():
    # TODO: create DB session, insert sample data
    print("TODO: seed development database")


if __name__ == "__main__":
    asyncio.run(seed())
