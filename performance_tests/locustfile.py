import base64
from io import BytesIO

from PIL import Image, ImageDraw
from locust import HttpUser, task, between

# Synthetic strokes for 나, the first exercise in the bundled backup.
SAMPLE_STROKES = [((17, 20), (17, 48), (29, 48)), ((43, 13), (43, 59)), ((43, 32), (57, 32))]


def encode_stroke(points):
    image = Image.new("RGBA", (72, 72))
    ImageDraw.Draw(image).line(points, fill="black", width=4)
    with BytesIO() as output:
        image.save(output, format="PNG")
        return base64.b64encode(output.getvalue()).decode("ascii")


SAMPLE_IMAGES = [encode_stroke(stroke) for stroke in SAMPLE_STROKES]
SAMPLE_ENDPOINTS = [
    {"x": point[0], "y": point[1]}
    for stroke in SAMPLE_STROKES
    for point in (stroke[0], stroke[-1])
]

class HandwritingUser(HttpUser):
    wait_time = between(1, 3)  # Users wait 1-3 seconds between tasks

    def on_start(self):
        """
        Locust 사용자가 시작될 때 호출됩니다.
        여기서 SSL 인증서 확인을 비활성화합니다.
        """
        self.client.verify = False # 모든 요청에 대해 SSL 인증서 확인 비활성화

    @task(5)
    def get_user_profile(self):
        """Test getting user profile (Light DB read)."""
        self.client.get("/api/user/getProfile/1", name="/api/user/getProfile/{id}")

    @task(2)
    def get_user_stats(self):
        """Test getting user statistics (Medium DB read)."""
        self.client.get("/api/user/stats/1", name="/api/user/stats/{id}")

    @task(2)
    def get_step_list(self):
        """Test getting step list (Static Data DB read)."""
        self.client.get("/api/data/step", name="/api/data/step")

    @task(1)
    def generate_text(self):
        """Test the text generation endpoint (Gemini API wrapper)."""
        payload = {
            "form": "WORD",
            "length": 3,
            "con": "받침이 없는 단어"
        }
        self.client.post("/api/text/generate", json=payload, name="/api/text/generate")

    @task(3)
    def evaluate_handwriting(self):
        """Test the handwriting evaluation endpoint (Heavy Compute)."""
        # Use a development DB where user_id=1 exists and step_id=1 is 나.
        payload = {
            "user_id": 1,
            "step_id": 1,
            "practice_text": "나",
            "cell_images": {"0": SAMPLE_IMAGES},
            "detailed_strokecounts": {"0": [1, 2, 0]},
            "firstandlast_stroke": {"0": SAMPLE_ENDPOINTS},
            "user_type": "CHILD",
        }

        self.client.post("/api/step/evaluate", json=payload, name="/api/step/evaluate")

