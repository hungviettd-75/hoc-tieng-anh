import asyncio
import websockets
import json

async def test_ws():
    # Thử kết nối tới Render production WebSocket
    uri = "wss://ai-english-coach-backend.onrender.com/api/v1/ws/1"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            # Gửi tin nhắn test
            test_message = {"content": "Hi, I want to learn English!"}
            await websocket.send(json.dumps(test_message))
            print("Sent test message:", test_message)
            
            # Nhận stream phản hồi
            print("Waiting for response stream...")
            with open("ws_result.txt", "w", encoding="utf-8") as f:
                for _ in range(30): # Nhận tối đa 30 chunks
                    response = await websocket.recv()
                    data = json.loads(response)
                    print("Received chunk type:", data.get("type"))
                    if "content" in data:
                        f.write(data["content"])
                        f.flush()
                    if data.get("type") == "completion":
                        print("Finished stream!")
                        break
            print("Saved output to ws_result.txt")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())

