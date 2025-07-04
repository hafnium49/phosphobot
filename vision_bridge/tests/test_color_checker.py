from fastapi.testclient import TestClient
from vision_bridge.main import app

if __name__ == "__main__":
    client = TestClient(app)
    with open("vision_bridge/samples/ColorCheckerClassic_24patch_sRGB.png", "rb") as f:
        response = client.post("/color-checker", files={"file": ("image.png", f, "image/png")})
    print(response.json())
