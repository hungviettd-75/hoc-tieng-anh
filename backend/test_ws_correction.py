import asyncio
import websockets
import json

async def test_client():
    uri = "ws://127.0.0.1:8000/api/v1/ws/realtime/1"
    async with websockets.connect(uri) as websocket:
        print("Connected!")
        
        # Send a message with a grammar error
        await websocket.send(json.dumps({
            "type": "message",
            "content": "I has a dog"
        }))
        
        try:
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Received: {data['type']}")
                if data['type'] == 'realtime_correction':
                    print(f"CORRECTION: {data['formatted_text']}")
                    for c in data['corrections']:
                        print(f"  - {c['explanation_vi']}")
                if data['type'] == 'done':
                    break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
