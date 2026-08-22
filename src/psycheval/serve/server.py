from __future__ import annotations

import sys

from psycheval.serve.constants import *  # noqa: F401,F403
from psycheval.serve.handler import *  # noqa: F401,F403
from psycheval.serve.lifecycle import *  # noqa: F401,F403
from psycheval.serve.path_picker import *  # noqa: F401,F403
from psycheval.serve.payloads import *  # noqa: F401,F403
from psycheval.serve.runtime import *  # noqa: F401,F403
from psycheval.serve.sources import *  # noqa: F401,F403

if __name__ == "__main__":
    print("psycheval.serve is not a standalone entry point", file=sys.stderr)
