import os
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
STRING_SESSION = os.getenv("STRING_SESSION", "")
TARGET_BOT = os.getenv("TARGET_BOT", "@tojitopupshopbot") # TOJI Bot ရဲ့ Username ထည့်ရန်

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
order_lock = asyncio.Lock()

class OrderRequest(BaseModel):
    player_id: str
    zone_id: str
    package: str

@app.on_event("startup")
async def startup_event():
    await client.start()
    print("✅ Xice Auto-Buy Userbot စတင်အလုပ်လုပ်နေပါပြီ!")

@app.get("/")
async def root():
    return {"status": "online", "message": "Xice Gaming Store Auto-Bot is running!"}

async def click_button_contains(message, search_text):
    if not message.buttons:
        return False
    for row_idx, row in enumerate(message.buttons):
        for col_idx, btn in enumerate(row):
            if search_text.lower() in btn.text.lower():
                await message.click(row_idx, col_idx)
                return True
    return False

@app.post("/api/order")
async def process_order(order: OrderRequest):
    async with order_lock:
        try:
            async with client.conversation(TARGET_BOT, timeout=45) as conv:
                await conv.send_message("/cancel")
                await asyncio.sleep(1)

                await conv.send_message("Special")
                resp_game = await conv.get_response()

                clicked_mlbb = await click_button_contains(resp_game, "MLBB (BR)")
                if not clicked_mlbb:
                    raise HTTPException(status_code=400, detail="MLBB (BR) ခလုတ် ရှာမတွေ့ပါ။")
                
                await asyncio.sleep(2)
                messages = await client.get_messages(TARGET_BOT, limit=1)
                prod_msg = messages[0]

                found_pkg = False
                for page in range(1, 5):
                    if await click_button_contains(prod_msg, order.package):
                        found_pkg = True
                        break
                    next_page = str(page + 1)
                    if await click_button_contains(prod_msg, next_page):
                        await asyncio.sleep(2)
                        messages = await client.get_messages(TARGET_BOT, limit=1)
                        prod_msg = messages[0]
                    else:
                        break

                if not found_pkg:
                    raise HTTPException(status_code=404, detail=f"Package '{order.package}' ကို ရှာမတွေ့ပါ။")

                await conv.get_response()
                await conv.send_message(order.player_id.strip())

                await conv.get_response()
                await conv.send_message(order.zone_id.strip())

                resp_verify = await conv.get_response()
                if "Player Verified" not in resp_verify.text and not resp_verify.buttons:
                    await asyncio.sleep(3)
                    messages = await client.get_messages(TARGET_BOT, limit=1)
                    resp_verify = messages[0]

                clicked_yes = await click_button_contains(resp_verify, "YES")
                if not clicked_yes:
                    raise HTTPException(status_code=400, detail=f"ID စစ်ဆေးမှု မအောင်မြင်ပါ: {resp_verify.text}")

                await asyncio.sleep(2)
                final_msgs = await client.get_messages(TARGET_BOT, limit=1)
                
                return {
                    "status": "success",
                    "verified_info": resp_verify.text,
                    "bot_reply": final_msgs[0].text
                }

        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="TOJI Bot ဘက်မှ အကြောင်းပြန်ချိန် ကြာနေပါသည်။")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
