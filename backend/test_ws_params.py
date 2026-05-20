import sys
import asyncio
import websockets
import json

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

async def test_client():
    uri = "ws://127.0.0.1:8000/api/v1/ws/realtime/1?mode=vocabulary_practice&level=A1&words=Beginner,Practice,Vocabulary,Improve"
    print(f"Connecting to: {uri}")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            await websocket.send(json.dumps({"type": "client_ready"}))
            print("Sent client_ready action")
            
            async def receive_messages():
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        if data.get("type") == "delta":
                            print(data.get("content"), end="", flush=True)
                        elif data.get("type") == "done":
                            print("\n\nDONE:", data)
                        else:
                            print("\nSTATUS:", data)
                except Exception as e:
                    print(f"\nReceive error: {e}")
            
            await asyncio.wait_for(receive_messages(), timeout=12.0)
    except asyncio.TimeoutError:
        print("\nTest completed (timeout).")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
