import base64
from pathlib import Path


LOGO_PATH = Path(__file__).resolve().parent / "assets" / "epespo-logo.png"
LOGO_NAVY_PATH = (
    Path(__file__).resolve().parent / "assets" / "epespo-logo-azul.png"
)
LOGO_DATA_URI = (
    "data:image/png;base64,"
    + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
)
LOGO_NAVY_DATA_URI = (
    "data:image/png;base64,"
    + base64.b64encode(LOGO_NAVY_PATH.read_bytes()).decode("ascii")
)
