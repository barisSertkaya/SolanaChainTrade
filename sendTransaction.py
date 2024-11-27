import asyncio
import requests
from redis.asyncio import Redis
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig
from solders.commitment_config import CommitmentLevel
from telegram import Bot

# Telegram bot ayarları
TELEGRAM_BOT_TOKEN = "xxxx"
TELEGRAM_CHAT_ID = "xxxx"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Redis bağlantısı
redis_client = Redis(host="xxx", port=6379)

# API URL'leri
PUMPFUN_URL = "https://pumpportal.fun/api/trade-local"
RPC_URL = "https://testnet.block-engine.jito.wtf/api/v1/transactions"


async def send_telegram_message(mint):
    message = f"<b>💲🤑💰Transaction confirmed!</b>\n\n<b>Mint Address:</b> {mint}\n\nURL: https://pump.fun/{mint}"
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="HTML")

# İşlem yapma fonksiyonu
async def buy_token(mint):

    response = requests.post(url=PUMPFUN_URL, data={
        "publicKey": "xxxx", # Solana wallet PublicKey
        "action": "buy",
        "mint": mint,
        "amount": 0.1,
        "denominatedInSol": "true",
        "slippage": 25,
        "priorityFee": 0.003,
        "pool": "pump"
    })

    if response.status_code == 200:

        # İşlem imzalama süreci

        keypair = Keypair.from_base58_string("xxxxx")  # Wallet base58 kodu
        tx = VersionedTransaction(VersionedTransaction.from_bytes(response.content).message, [keypair])

        commitment = CommitmentLevel.Confirmed
        config = RpcSendTransactionConfig(preflight_commitment=commitment)
        
        # İmzalı işlemi RPC endpoint'e gönder
        response = requests.post(
            url=RPC_URL,
            headers={"Content-Type": "application/json"},
            data=SendVersionedTransaction(tx, config).to_json()
        )
        
        if response.status_code == 200:
            tx_signature = response.json()['result']
            print(f'Transaction successfully sent: https://solscan.io/tx/{tx_signature}')
            #await redis_client.publish("buyed-channel", mint)  # Fiyat bilgisi takibi için Redis kanalına gönderim 
            await send_telegram_message(mint, tx_signature)
        else:
            print("Error sending transaction:", response.json())
    else:
        print("Error in buying token:", response.json())

async def redis_subscriber():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("in-mint-channel")

    async for message in pubsub.listen():
        if message['type'] == 'message':
            mint_address = message['data'].decode('utf-8')

            await buy_token(mint_address)

async def main():
    await redis_subscriber()

if __name__ == "__main__":
    asyncio.run(main())