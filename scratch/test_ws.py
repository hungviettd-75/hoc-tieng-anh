import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://127.0.0.1:8000/api/v1/ws/1"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket")
            await websocket.send(json.dumps({"content": "Hello"}))
            print("Message sent")
            response = await websocket.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
