import asyncio
import json
import redis
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

r = redis.Redis(host='xxx', port=6379, db=0)  # Redis Database

async def process_message(message):
    try:
        data = json.loads(message)

        if 'traderPublicKey' in data:
            trader_public_key = data['traderPublicKey']
        
            if r.sismember("mint-tokens", trader_public_key):
                mint = data.get("mint")
                # Mint adresini Redis kanalına yayınla
                r.publish("in-mint-channel", mint)

    except Exception as e:
        print(f"Message processing error: {e}")

# WebSocket bağlantısını kuran ve mesajları dinleyen fonksiyon
async def connect_websocket(url, retry_interval=5):
    while True:
        try:
            async with websockets.connect(url) as ws:
                print("WebSocket bağlantısı kuruldu.")
                
                payload = {
                    "method": "subscribeNewToken",
                }
                await ws.send(json.dumps(payload))
                print("Abonelik mesajı gönderildi.")
                
                async for message in ws:
                    await process_message(message)
        except (ConnectionClosedError, ConnectionClosedOK) as e:
            print(f"WebSocket bağlantısı kapandı: {e}")
            print(f"{retry_interval} saniye sonra yeniden bağlanılıyor...")
            await asyncio.sleep(retry_interval)
        except Exception as e:
            print(f"WebSocket hatası: {e}")
            print(f"{retry_interval} saniye sonra yeniden bağlanılıyor...")
            await asyncio.sleep(retry_interval)

async def main():
    websocket_url = "wss://pumpportal.fun/api/data"
    await connect_websocket(websocket_url)

if __name__ == "__main__":
    asyncio.run(main())