import asyncio
import json
import logging
import os

import websockets
from dotenv import load_dotenv
from telegram import Bot


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", ".env"
    )
)

URL = os.getenv("URL")
THRESHOLD = int(os.getenv("THRESHOLD", 50000))
# BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL")


# bot = Bot(token=BOT_TOKEN)


async def gate_data(raw_data):
    if raw_data.get("e") == "forceOrder":
        avg_price = float(raw_data["o"]["ap"])
        orig_quantity = float(raw_data["o"]["q"])

        liq_value = avg_price * orig_quantity

        if liq_value >= THRESHOLD:
            await process_message(raw_data, liq_value, avg_price)
    else:
        logging.error("gateData Error!: rawData is Not 'forceOrder'.")


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
    # try:
    #     await bot.send_message(CHANNEL_ID, text=message)
    #     logging.info(f"sendMessage: {message}")
    # except Exception as e:
    #     logging.error(f"sendMessage Error!: {e}")
    print(message)


async def handle_websocket():
    connection_tried = 0

    while True:
        try:
            async with websockets.connect(URL) as ws:
                logging.info("✅ WebSocket Connected.")
                connection_tried = 0

                async for message in ws:
                    try:
                        data = json.loads(message)
                        await gate_data(data)
                    except json.JSONDecodeError as e:
                        logging.warning(
                            f"⚠️ JSON Decode Error: {e} | Raw message: {message}"
                        )
                    except Exception as e:
                        logging.error(
                            f"❌ Error Processing Message: {e} | Message: {message}"
                        )
        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ) as e:
            logging.warning(f"❌ WebSocket Connection Closed: {e}")
        except Exception as e:
            logging.error(f"⚠️ WebSocket Connection Error: {e}")

        if connection_tried <= 5:
            logging.info("🔁 Reconnecting Websocket...")
            connection_tried += 1
            await asyncio.sleep(5)
        else:
            await send_message("Bot Stopped.")
            logging.error("❌ Maximum econnect attempts reached. Exiting.")
            break


# async def main():
#     await handle_websocket()


if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)
        loop.run_until_complete(handle_websocket())
    except KeyboardInterrupt:
        logging.info("⚠️ KeyboardInterrupt received. Exiting gracefully...")
    finally:
        pending = asyncio.all_tasks(loop)

        for task in pending:
            task.cancel()

        logging.info("⚠️ Cancelling pending tasks...")

        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

        logging.info("✅ Event loop closed cleanly.")
