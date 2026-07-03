"""Environment fixes so reproducibly-installable OSS rivals import & run here.

pywinauto pulls in comtypes, whose generated type-library cache defaults to a
read-only ``site-packages/comtypes/gen`` under a system Python (PermissionError)
and can go stale ("Typelib different than module"). naturo self-heals this
(#1219/#1220); the rivals do not. Call :func:`prepare_comtypes_gen` before
importing pywinauto so its comtypes writes to a fresh, writable gen dir.
"""
from __future__ import annotations

import os
import sys
import tempfile


def prepare_comtypes_gen() -> str:
    """Point comtypes' generated cache at a fresh writable dir. Returns the dir.

    Idempotent-ish: a new temp dir each call, which is fine for a benchmark run.
    """
    gen_dir = tempfile.mkdtemp(prefix="naturo_bench_ctgen_")
    os.environ["COMTYPES_GEN_DIR"] = gen_dir
    try:
        import comtypes
        import comtypes.client
        comtypes.client.gen_dir = gen_dir
        import comtypes.gen
        comtypes.gen.__path__ = [gen_dir]  # force lookups into the empty dir
        for mod in [m for m in sys.modules if m.startswith("comtypes.gen.")]:
            del sys.modules[mod]
    except Exception:
        pass
    return gen_dir
