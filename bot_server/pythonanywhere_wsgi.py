import sys
from pathlib import Path

from a2wsgi import ASGIMiddleware

project_home = Path(__file__).resolve().parent
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from app.main import app as asgi_app  # noqa: E402

application = ASGIMiddleware(asgi_app)
