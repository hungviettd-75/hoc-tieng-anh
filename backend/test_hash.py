from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
stored_hash = "$2b$12$v1wUsEDdiz7TWJOpQKhf0OLsmmDCYcL25WjyBYz1gXvKp9c6Rg7w2"
password = "hung123"

verified = pwd_context.verify(password, stored_hash)
print(f"Password 'hung123' verification result: {verified}")
