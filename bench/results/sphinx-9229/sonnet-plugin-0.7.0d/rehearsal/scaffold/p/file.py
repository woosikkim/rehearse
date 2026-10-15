from pathlib import Path
from typing import Any, Callable, Dict, Union

ScaffoldOpts = Dict[str, Any]
"""Doc of opts."""

FileContents = Union[str, None]
"""Doc of contents."""

FileOp = Callable[[Path, FileContents, ScaffoldOpts], Union[Path, None]]
"""Doc of fileop."""
class Foo:
    """Foo doc"""

Bar = Foo
"""Doc of Bar alias."""
