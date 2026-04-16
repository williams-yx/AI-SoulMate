import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("No DATABASE_URL")
        return
        
    conn = await asyncpg.connect(url)
    assets = await conn.fetch("SELECT id, model_url FROM assets WHERE model_url NOT LIKE 'oss://%'")
    print(f"Non-OSS assets: {len(assets)}")
    
    history = await conn.fetch("SELECT id, preview_url FROM studio_history WHERE preview_url NOT LIKE 'oss://%' AND preview_url IS NOT NULL")
    print(f"Non-OSS history: {len(history)}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
