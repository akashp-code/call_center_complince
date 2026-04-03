import base64

with open("clean.mp3", "rb") as f:
    encoded = base64.b64encode(f.read()).decode("utf-8")

# SAVE TO FILE INSTEAD OF PRINT
with open("output.txt", "w") as f:
    f.write(encoded)

print("Base64 saved to output.txt")