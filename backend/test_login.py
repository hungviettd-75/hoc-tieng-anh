
import requests

url = "http://127.0.0.1:8000/api/v1/auth/login"
data = {
    "username": "hunghvc@aicoach.com",
    "password": "password" # I don't know the password, let's hope it's 'password' or just see if it returns 400
}

try:
    response = requests.post(url, data=data, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Body: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
