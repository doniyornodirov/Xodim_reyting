import asyncio
import logging
from fastapi import FastAPI
import uvicorn
from bot import main as start_bot, bot

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Bot va Server muvaffaqiyatli ishlamoqda!"}

async def run_fastapi():
    config = uvicorn.Config(app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    # Telegram bot va FastAPI serverini bir vaqtning o'zida (parallel) ishga tushiramiz
    await asyncio.gather(
        start_bot(),
        run_fastapi()
    )

if __name__ == "__main__":
    asyncio.run(main())