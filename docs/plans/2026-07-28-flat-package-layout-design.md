# ShockLink Flat Package Layout Design

## Goal

`src/shocklink/` must contain no subdirectories. The package will use one
top-level Python module per scientific domain while preserving the existing
public imports.

## Layout

```text
src/shocklink/
├── __init__.py
├── bowshock.py
├── config.py
├── connectivity.py
├── core.py
├── exceptions.py
├── fieldlines.py
├── io.py
└── py.typed
```

Future integrations will follow the same rule. For example, ParaView and CLI
support will use `paraview.py` and `cli.py`, not package directories.

## Compatibility

The domain names remain unchanged, so imports such as:

```python
from shocklink.bowshock import BowShockSurface
from shocklink.connectivity import ConnectivityResult
from shocklink.core import CoordinateSystem
```

continue to work after `bowshock/`, `connectivity/`, and `core/` become
`bowshock.py`, `connectivity.py`, and `core.py`.

Internal imports will target the flat modules. There will be no compatibility
for private implementation paths such as `shocklink.bowshock.models`; those
paths were never part of the public API.

## Verification

A structural regression test will inspect the installed source package and fail
if any directory exists directly inside `src/shocklink/`. The existing behavior
tests will continue to verify the public imports and scientific model
invariants.

Generated directories such as `__pycache__` will be removed before structural
verification. Repository ignore rules will continue to prevent their accidental
commit, but test execution may recreate them at runtime; the regression test
will therefore inspect the tracked source layout rather than runtime cache
artifacts.
