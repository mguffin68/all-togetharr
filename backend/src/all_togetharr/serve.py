import uvicorn

from all_togetharr.platform.logging import configure_logging
from all_togetharr.platform.settings import Settings


def main() -> None:
    settings = Settings()
    configure_logging(settings)
    uvicorn.run(
        "all_togetharr.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8080,
        log_config=None,
    )


if __name__ == "__main__":
    main()
