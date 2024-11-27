import asyncio
import json
import logging
import os

import websockets
from dotenv import load_dotenv
from telegram import Bot

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
load_dotenv(dotenv_path=os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', '.env'))

URL = os.getenv("URL")
THRESHOLD = int(os.getenv("THRESHOLD", 50000))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL")
bot = Bot(token=BOT_TOKEN)


async def dataGate(rawData):
    if rawData.get('e') == 'forceOrder':
        avgPrice = float(rawData['o']['ap'])
        origQuantity = float(rawData['o']['q'])

        liqValue = avgPrice * origQuantity

        if liqValue >= THRESHOLD:
            await processMessage(rawData, liqValue, avgPrice)
    else:
        logging.error("gateData Error!: rawData is Not 'forceOrder'.")


def getEmoji(liqValue):
    if liqValue >= 10000000:
        return "🔥🔥🔥"
    elif liqValue >= 1000000:
        return "🔥🔥"
    elif liqValue >= 100000:
        return "🔥"
    else:
        return ""


async def processMessage(rawData, liqValue, avgPrice):
    symbol = rawData['o']['s']
    side = "Long" if rawData['o']['S'] == "SELL" else "Short"
    chartEmoji = "📉" if side == "Long" else "📈"
    liqPrice = f"{avgPrice:.8g}"
    formatted_liqValue = f"{liqValue:,.2f}"
    fireEmoji = getEmoji(liqValue)

    liqMessage = (
        f"{chartEmoji} #{symbol} Liquidated {side} at\n"
        f"${liqPrice}: ${formatted_liqValue}{fireEmoji}"
    )

    await sendMessage(liqMessage)


async def sendMessage(liqMessage):
    try:
        await bot.send_message(CHANNEL_ID, text=liqMessage)
        logging.info(f"sendMessage: {liqMessage}")
    except Exception as e:
        logging.error(f"sendMessage Error!: {e}")


async def connectWebsocket():
    while True:
        try:
            async with websockets.connect(URL) as ws:
                logging.info("WebSocket Opened.")

                while True:
                    await dataGate(json.loads(await ws.recv()))
        except websockets.exceptions.ConnectionClosedError as e:
            logging.warning(f"WebSocket Closed. ({e})")
        except Exception as e:
            logging.error(f"Websocket Error! ({e})")

        logging.info("Websocket Connecting...")
        await asyncio.sleep(5)


async def main():
    await connectWebsocket()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt...")
