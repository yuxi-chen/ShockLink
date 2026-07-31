# Optional GSM coordinates for MMS vectors

## Goal

Keep GSE as the default coordinate system for the MMS example while allowing
users to select GSM consistently through the Python API, command-line
interface, and notebook.

## Approach

Continue downloading the existing GSE FGM and FPI products, then use
pySPEDAS `cotrans` for the time-dependent GSE-to-GSM rotation when GSM is
requested. This keeps magnetic-field and velocity handling on one path and
preserves the tplot-variable workflow used by plotting and summaries.

Requesting native GSM products was rejected because availability differs
between FGM and FPI. Transforming NumPy arrays during plotting was rejected
because it couples a scientific operation to visualization and discards tplot
metadata. MMS quaternion conversion was rejected because spacecraft attitude
transformations are unnecessary for a geophysical GSE-to-GSM conversion.

## Interface

Add a `coordinates` argument to `load_mms_data`:

```python
load_mms_data(
    start,
    end,
    probe=1,
    mode="auto",
    coordinates="gse",
)
```

The accepted values are `"gse"` and `"gsm"`; GSE remains the default. The CLI
adds `--coordinates {gse,gsm}`, and the notebook exposes a `COORDINATES`
setting that is passed to `load_mms_data`.

`MMSData` records the selected frame with a backward-compatible default:

```python
@dataclass(frozen=True)
class MMSData:
    cadence: Cadence
    series: Mapping[str, str]
    probe: int | None = None
    coordinates: str = "gse"
```

## Data flow

Validate the coordinate choice before downloading data. The default loader
continues requesting GSE magnetic-field and FPI moment variables. For a GSE
request, return those variables unchanged. For a GSM request, pass every
loaded vector variable to pySPEDAS `cotrans` with `coord_in="gse"` and
`coord_out="gsm"`.

The converted set includes magnetic field, ion bulk velocity, and electron
bulk velocity, even though electron velocity is not plotted by default.
Density and temperature products are scalars and remain unchanged. Output
variable names replace the exact `_gse_` token with `_gsm_`; if a source name
does not contain that token, append `_gsm`. The returned series mapping points
to the converted variables, so summaries and plots use one internally
consistent coordinate frame.

Coordinate conversion happens after each cadence request has produced usable
data. Automatic burst-to-fast fallback therefore remains unchanged.

## Plotting and metadata

The figure title identifies the selected frame, for example:

```text
MMS1 fast data (GSM)
```

Vector colors remain blue, green, red, and black for X, Y, Z, and magnitude.
Summary documentation refers to components in the selected coordinate system
instead of hard-coding GSE.

## Failure handling

An unsupported coordinate name raises `ValueError` before any loader call. If
pySPEDAS fails to create a requested transformed vector, raise `RuntimeError`
that identifies the source product. Never return a partially transformed
mapping labeled as GSM.

Missing optional vector products remain acceptable: only vectors actually
loaded for the interval are transformed.

## Tests and documentation

Unit tests will mock the pySPEDAS loader and coordinate transform, requiring no
network access. Coverage will verify:

- GSE remains the default and performs no transformation;
- only `gse` and `gsm` are accepted by the API and CLI;
- GSM transforms all loaded vectors and leaves scalars unchanged;
- transformed variables receive deterministic GSM names;
- conversion failures are reported without returning mixed coordinates;
- the coordinate choice is retained by `MMSData` and shown in plot titles; and
- the notebook exposes and forwards its coordinate setting.

The example README will document both the default and the GSM opt-in usage.
