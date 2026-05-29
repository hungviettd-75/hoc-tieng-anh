import google.generativeai as genai

key = "AIzaSyDCdSVoziJ_Yl3Nn5zKdMqn74ydJQuTdcY"
genai.configure(api_key=key)

models = [
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-2.0-flash-lite',
    'gemini-3.1-flash-lite',
    'gemini-3.5-flash'
]

for model_name in models:
    print(f"\n--- Testing model: {model_name} ---")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, are you active? Please reply in 3 words.")
        print(f"Success! Response: {response.text.strip()}")
    except Exception as e:
        print(f"Failed! Error: {e}")
