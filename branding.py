import base64
from pathlib import Path


LOGO_PATH = Path(__file__).resolve().parent / "assets" / "epespo-logo.png"
LOGO_DATA_URI = (
    "data:image/png;base64,"
    + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
)
