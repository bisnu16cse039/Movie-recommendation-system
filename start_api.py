"""Start the FastAPI server"""

import uvicorn
from config.settings import Settings

if __name__ == "__main__":
    # Load settings
    settings = Settings.from_yaml()
    
    # Start server
    uvicorn.run(
        "api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers,
        log_level="info"
    )
