import os
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

from app.router_logic import router_logic

load_dotenv()

app = FastAPI(title="Festo LINE Bot")

# Use Mock if keys are missing
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

is_mock_line = False
if not LINE_CHANNEL_ACCESS_TOKEN or "your_line" in LINE_CHANNEL_ACCESS_TOKEN:
    print("WARNING: LINE credentials missing. Using MOCK mode for Webhook.")
    is_mock_line = True
    line_bot_api = None
    handler = None
else:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.get("/")
def root():
    return {"status": "ok", "message": "Festo LINE Bot Service is running."}

@app.post("/callback")
async def callback(request: Request):
    if is_mock_line:
        body = await request.body()
        print(f"Mock Received Webhook: {body.decode('utf-8')}")
        return "OK"

    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"

if not is_mock_line:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        user_message = event.message.text
        user_id = event.source.user_id
        
        # Route message through our logic
        reply_text = router_logic.process_message(user_id, user_message)
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
