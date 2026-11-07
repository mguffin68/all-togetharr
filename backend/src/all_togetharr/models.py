"""All model imports live here so Base.metadata is complete."""

import all_togetharr.platform.auth.models  # noqa: F401
import all_togetharr.platform.jobs.models  # noqa: F401
import all_togetharr.platform.settings_store  # noqa: F401
from all_togetharr.platform.db import Base

__all__ = ["Base"]
