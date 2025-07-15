import asyncio
import os

import uvicorn

from src import app
from src.app import HOST, PORT

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
else:
    try:
        import uvloop

        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    except ImportError:
        pass

if __name__ == "__main__":
    uvicorn.run("src:app", host=HOST, port=int(PORT), reload=True)
