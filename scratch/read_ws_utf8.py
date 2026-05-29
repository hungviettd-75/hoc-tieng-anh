import asyncio
import websockets
import json
import sys

# Thiết lập mã hóa utf-8 cho console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def test_ws():
    uri = "wss://ai-english-coach-backend.onrender.com/api/v1/ws/1"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri, open_timeout=20) as websocket:
            print("Connected successfully!")
            test_message = {"content": "Hi, I want to learn English!"}
            await websocket.send(json.dumps(test_message))
            print("Sent test message:", test_message)
            
            print("Waiting for response stream...")
            full_response = ""
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                
                # In ra chunk nhận được
                chunk_type = data.get("type")
                content = data.get("content", "")
                
                if chunk_type == "delta":
                    print(content, end="", flush=True)
                    full_response += content
                elif chunk_type == "completion":
                    print("\n\n--- COMPLETED ---")
                    print(f"Full response length: {len(full_response)}")
                    break
                elif "error" in data:
                    print(f"\nError from server: {data['error']}")
                    break
    except Exception as e:
        print(f"\nConnection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
