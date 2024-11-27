import json
import asyncio
import websockets
import redis.asyncio as redis
from telegram import Bot

TELEGRAM_BOT_TOKEN = "xxx"
TELEGRAM_CHAT_ID = "xxx"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

websocket_url = "wss://pumpportal.fun/api/data"
redis_url = "xxx"

mint_data = {}
keys = set()
update_queue = asyncio.Queue()

redis_client = redis.from_url(redis_url)

async def send_telegram_message(mint, initial_price, max_price, current_price, gain_from_initial, drop_from_max):
    message = (
        f"<b>⚠️ Price Drop Alert</b>\n\n"
        f"<b>Mint Address:</b> {mint}\n"
        f"<b>Initial Price:</b> {initial_price}\n"
        f"<b>Max Price:</b> {max_price}\n"
        f"<b>Current Price:</b> {current_price}\n"
        f"<b>Gain from Initial:</b> {gain_from_initial:.2f}%\n"
        f"<b>Drop from Max:</b> {drop_from_max:.2f}%\n\n"
        f"URL: https://pump.fun/{mint}"
    )
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")
    except Exception as e:
        print(f"Telegram mesajı gönderilemedi. Hata: {e}")

async def handle_new_mint(mint_address):
    if mint_address not in mint_data:
        keys.add(mint_address)
        mint_data[mint_address] = {"initial_price": None, "max_price": None}
        update_queue.put_nowait(True)  # WebSocket'e güncelleme gönder

async def subscribe_to_trades():
    while True:
        try:
            async with websockets.connect(websocket_url, ping_interval=20, ping_timeout=20) as ws:
                asyncio.create_task(handle_trade_messages(ws))

                while True:
                    await update_queue.get()  # Güncelleme sinyalini bekle
                    if keys:
                        payload = {"method": "subscribeTokenTrade", "keys": list(keys)}
                        await ws.send(json.dumps(payload))
        except websockets.ConnectionClosedError as e:
            print("WebSocket bağlantısı kapandı, yeniden bağlanıyor:", e)
            await asyncio.sleep(5)

async def handle_trade_messages(ws):
    try:
        async for message in ws:
            data = json.loads(message)
            await handle_trade_message(data)
    except websockets.ConnectionClosedError as e:
        print("Veri okuma sırasında WebSocket bağlantısı kapandı:", e)

async def handle_trade_message(data):
    mint = data.get('mint')
    market_cap_sol = data.get('marketCapSol')

    if mint is None or market_cap_sol is None:
        print("Gelen veri eksik, işlenmiyor:", data)
        return

    if mint not in keys:
        return

    mint_info = mint_data[mint]

    if mint_info["initial_price"] is None:
        mint_info["initial_price"] = market_cap_sol
        mint_info["max_price"] = market_cap_sol

    if market_cap_sol > mint_info["max_price"]:
        mint_info["max_price"] = market_cap_sol

    gain_from_initial = (mint_info["max_price"] - mint_info["initial_price"]) / mint_info["initial_price"] * 100
    drop_from_max = (mint_info["max_price"] - market_cap_sol) / mint_info["max_price"] * 100

    if drop_from_max >= 10:
        await send_telegram_message(
            mint,
            mint_info["initial_price"],
            mint_info["max_price"],
            market_cap_sol,
            gain_from_initial,
            drop_from_max
        )
        await remove_mint(mint)

async def remove_mint(mint):
    keys.discard(mint)
    if mint in mint_data:
        del mint_data[mint]
    update_queue.put_nowait(True)

async def redis_subscriber():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("in-mint-channel")

    async for message in pubsub.listen():
        if message['type'] == 'message':
            mint_address = message['data'].decode('utf-8')
            await handle_new_mint(mint_address)

async def main():
    await asyncio.gather(subscribe_to_trades(), redis_subscriber())

asyncio.run(main())
