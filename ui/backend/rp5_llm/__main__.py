"""Run the management process. llama-server is a separate program."""

from __future__ import annotations

import uvicorn

from rp5_llm.app import create_app
from rp5_llm.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.bind, port=settings.port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()
