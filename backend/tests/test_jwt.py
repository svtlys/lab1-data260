"""
test JWT creation and decoding.
"""

from app.core.security import create_access_token, decode_access_token


# create a token for a sample student user
access_token = create_access_token(
    subject="1",
    role="student",
)

# decode the token and display the stored claims
decoded_token = decode_access_token(access_token)

print("token created:", access_token.startswith("ey"))
print("subject:", decoded_token["sub"])
print("role:", decoded_token["role"])
print("token contains expiration:", "exp" in decoded_token)