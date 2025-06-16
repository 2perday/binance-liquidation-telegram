import asyncio
import json
import logging
import os

from websockets.asyncio.client import connect
from dotenv import load_dotenv
from telegram import Bot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

URL = os.getenv("URL")
THRESHOLD = int(os.getenv("THRESHOLD", 50000))  # default: 50k
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")


bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def gate_data(raw_data):
    if raw_data.get("e") == "forceOrder":
        avg_price = float(raw_data["o"]["ap"])
        orig_quantity = float(raw_data["o"]["q"])

        liq_value = avg_price * orig_quantity

        if liq_value >= THRESHOLD:
            await process_message(raw_data, liq_value, avg_price)
    else:
        logging.error("gate_data Error!: raw_data is Not 'forceOrder'.")


def get_emoji(liq_value):
    if liq_value >= 10000000:
        return "🔥🔥🔥"
    elif liq_value >= 1000000:
        return "🔥🔥"
    elif liq_value >= 100000:
        return "🔥"
    else:
        return ""


async def process_message(raw_data, liq_value, avg_price):
    symbol = raw_data["o"]["s"]
    side = "Long" if raw_data["o"]["S"] == "SELL" else "Short"
    chart_emoji = "📉" if side == "Long" else "📈"
    liq_price = f"{avg_price:.8g}"
    formatted_liqValue = f"{liq_value / 1000:,.1f}"
    fire_emoji = get_emoji(liq_value)

    liq_message = (
        f"{chart_emoji} #{symbol} Liquidated {side}\n"
        f"${formatted_liqValue}K{fire_emoji} at {liq_price}"
    )

    await send_message(liq_message)


async def send_message(message):
    try:
        await bot.send_message(TELEGRAM_CHANNEL, text=message)
        logging.info(f"send_message: {message}")
    except Exception as e:
        logging.error(f"send_message Error!: {e}")


async def main():
    while True:
        try:
            async with connect(URL) as ws:
                logging.info("✅ WebSocket Connected.")

                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    await gate_data(data)
        except asyncio.CancelledError:
            logging.info("✅ WebSocket Connection Closed.")
            raise
        except Exception as e:
            logging.error(f"❌ WebSocket Connection Error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("✅ KeyboardInterrupt received.")
