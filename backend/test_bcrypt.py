from passlib.context import CryptContext
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password = "testpassword"
hashed = pwd_context.hash(password)
print(f"Hashed: {hashed}")
verified = pwd_context.verify(password, hashed)
print(f"Verified: {verified}")
