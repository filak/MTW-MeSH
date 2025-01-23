import os
import secrets

print("\n")

print("SECRET_KEY: ")
print(os.urandom(24))

print("\n")

print("SECRET_TOKEN_OR_SALT: ")
print(secrets.token_urlsafe())

print("\n")
