import uvicorn

from fantomex.api import app
from fantomex.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level)
