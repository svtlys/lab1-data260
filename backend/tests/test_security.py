"""
test the password hashing helpers.
"""

from app.core.security import hash_password, verify_password


# create a temporary test hash
password_hash = hash_password("Week1TestPassword!")

# display the results of the security checks
print("hash created:", password_hash.startswith("$2"))
print(
    "correct password:",
    verify_password("Week1TestPassword!", password_hash),
)
print(
    "wrong password:",
    verify_password("WrongPassword!", password_hash),
)