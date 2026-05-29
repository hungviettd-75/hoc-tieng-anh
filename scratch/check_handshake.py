import asyncio
import websockets
import sys

# Thiết lập mã hóa utf-8 cho console output trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def test_handshake():
    uri = "wss://ai-english-coach-backend.onrender.com/api/v1/ws/1?mode=vocabulary_practice&level=A1"
    print(f"Attempting handshake with {uri}...")
    try:
        # Đặt open_timeout cực ngắn để tránh bị treo
        async with websockets.connect(uri, open_timeout=5.0) as websocket:
            print("HANDSHAKE SUCCESSFUL! WebSocket connection established.")
            # Nhận 1 message chào mừng nếu có
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"Received initial message: {msg[:100]}...")
            except asyncio.TimeoutError:
                print("No initial welcome message received within 3s, but connection is open.")
    except Exception as e:
        print(f"HANDSHAKE FAILED: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test_handshake())
