"""Decoders for families stored as WFDB (and the PPG and capnography families that accept EDF too)."""
import math

from ..aliases import _aliases_for, _resolve_label
from ._util import _edf_signals, _manifest_one, _manifest_wfdb
from .edf import _read_role_edf
from ..errors import BadRequest, Degraded


# The twelve leads ecg-12lead-500hz-mv declares, in the order it declares them.
# Alignment is by name and never by position, so a source may order them any way
# it likes: PTB-XL writes AVL before AVF, and the family writes aVF before aVL.
_ECG_12LEAD_CHANNELS = ("I", "II", "III", "aVR", "aVF", "aVL",
                        "V1", "V2", "V3", "V4", "V5", "V6")
_ECG_12LEAD_RATE_HZ = 500
_ECG_12LEAD_UNITS = "mV"


def _read_wfdb_12lead(path, root):
    """A WFDB record -> the twelve named leads ecg-12lead-500hz-mv declares.

    `path` names the header. A record is two files, and the header is the half
    that says what the other half means, so it is the half a request names.

    The protocol is {format: wfdb, channels: 12 named leads, rate_hz: 500,
    units: mV, ndim: 2}. Conformance is verified and never inferred. A file that
    does not conform degrades; it is not resampled or rescaled into something
    plausible.
    """
    try:
        import numpy as np
        import wfdb
    except ImportError as exc:          # a build error, not a caller error
        raise RuntimeError(f"this image has no waveform library: {exc}")

    if path.suffix != ".hea":
        raise Degraded(
            f"a wfdb request names the header; '{path.name}' is not a .hea file")

    notes = []
    base = path.with_suffix("")
    try:
        header = wfdb.rdheader(str(base))
    except Exception as exc:
        raise Degraded(f"the file is not a readable wfdb header: {exc}")

    # Reject two source channels that map to one family lead. Selecting the last
    # one would make the output depend on file order, which the family forbids.
    declared = {name.casefold(): name for name in _ECG_12LEAD_CHANNELS}
    mapped = [declared.get(str(name).strip().casefold())
              for name in (header.sig_name or [])]
    duplicate = sorted({name for name in mapped if name and mapped.count(name) > 1})
    if duplicate:
        raise Degraded("the record declares a lead more than once: "
                       + ", ".join(duplicate))

    # The header names the files that hold the samples. Those names are input,
    # so they are confined exactly as the requested path was. Without this a
    # header could name any file the container can reach.
    for name in dict.fromkeys(header.file_name or []):
        target = (path.parent / name).resolve()
        if target != root and root not in target.parents:
            raise BadRequest(f"the header names a file outside DATA_ROOT: '{name}'")

    try:
        signals, fields = wfdb.rdsamp(str(base))
    except Exception as exc:
        raise Degraded(f"the record's samples could not be read: {exc}")

    rate = fields.get("fs")
    if rate != _ECG_12LEAD_RATE_HZ:
        raise Degraded(f"the record is {rate} Hz, the family declares "
                       f"{_ECG_12LEAD_RATE_HZ} Hz")
    if signals.ndim != 2:
        raise Degraded(f"the record has {signals.ndim} dimensions, the family declares 2")
    if signals.shape[0] == 0:
        raise Degraded("the record has no samples")

    # Source spelling is the source's business. Match on a folded name and
    # return the family's spelling, so no adapter ever sees 'AVR'.
    units = fields.get("units") or []
    channels, bad_units, extra = {}, [], []
    for index, source_name in enumerate(fields.get("sig_name") or []):
        name = declared.get(str(source_name).strip().casefold())
        if name is None:
            extra.append(str(source_name))
            continue
        unit = str(units[index]).strip() if index < len(units) else ""
        if unit != _ECG_12LEAD_UNITS:
            bad_units.append(f"{name} in {unit or 'no unit'}")
            continue
        channels[name] = np.asarray(signals[:, index], dtype=np.float64)

    if bad_units:
        raise Degraded(f"the family declares {_ECG_12LEAD_UNITS}, and the record "
                       f"gives " + ", ".join(bad_units))
    missing = [name for name in _ECG_12LEAD_CHANNELS if name not in channels]
    if missing:
        raise Degraded("the family declares twelve leads, and the record is "
                       f"missing {', '.join(missing)}")
    if extra:
        notes.append("channels not read, not declared by the family: "
                     + ", ".join(sorted(extra)))

    absent = sorted(name for name, values in channels.items()
                    if not np.isfinite(values).any())
    if absent:
        notes.append("leads present in the header but carrying no finite sample: "
                     + ", ".join(absent))

    return {"kind": "waveform", "channels": channels,
            "order": list(_ECG_12LEAD_CHANNELS),
            "rate_hz": float(rate), "units": _ECG_12LEAD_UNITS,
            "n_samples": int(signals.shape[0]), "notes": notes}


def _read_ppg(path, root):
    import numpy as np
    family = 'ppg-waveform-uncal'
    if path.suffix.lower() == '.edf':
        selected = [s for s in _edf_signals(path)
                    if _resolve_label(family, s.label)[0] == 'pleth']
        if len(selected) != 1:
            raise Degraded('EDF must contain exactly one named PPG channel')
        signal = selected[0]
        values, rate = signal.data, signal.sampling_frequency
    elif path.suffix.lower() == '.hea':
        import wfdb
        manifest = _manifest_wfdb(path, root)
        if manifest is None or any(not p.is_file() for p in manifest):
            raise Degraded('PPG requires a complete single-segment WFDB record')
        try:
            header = wfdb.rdheader(str(path.with_suffix('')))
            selected = [i for i, name in enumerate(header.sig_name)
                        if _resolve_label(family, name)[0] == 'pleth']
            if len(selected) != 1:
                raise Degraded('WFDB must contain exactly one named PPG channel')
            record = wfdb.rdrecord(str(path.with_suffix('')), channels=selected)
            values, rate = record.p_signal[:, 0], record.fs
        except (ValueError, OSError) as exc:
            raise Degraded(f'cannot read PPG waveform: {exc}') from exc
    else:
        raise Degraded('PPG requests name an EDF file or WFDB .hea header')
    if not math.isfinite(rate) or rate <= 0:
        raise Degraded('PPG sample rate must be positive and finite')
    values = np.asarray(values, dtype=float)
    return {'kind': 'waveform', 'channels': {'pleth': values}, 'order': ['pleth'],
            'rate_hz': float(rate), 'units': None, 'n_samples': len(values),
            'notes': ['PPG amplitude is uncalibrated; native sample rate retained']}


def _manifest_ppg(path, root):
    return _manifest_wfdb(path, root) if path.suffix.lower() == '.hea' else _manifest_one(path, root)



def _read_abp(path, root):
    import numpy as np
    import wfdb
    manifest = _manifest_wfdb(path, root)
    if manifest is None or any(not p.is_file() for p in manifest):
        raise Degraded('ABP requires a complete single-segment WFDB record')
    try:
        header = wfdb.rdheader(str(path.with_suffix('')))
        chosen = [i for i, n in enumerate(header.sig_name) if n.upper() in ('ABP', 'ART', 'AO', 'FAP', 'UAP')]
        if len(chosen) != 1:
            raise Degraded('ABP requires exactly one named arterial pressure channel')
        record = wfdb.rdrecord(str(path.with_suffix('')), channels=chosen)
    except (ValueError, OSError) as exc:
        raise Degraded(f'cannot read arterial pressure: {exc}') from exc
    if record.units != ['mmHg']:
        raise Degraded('ABP must use mmHg')
    x = np.asarray(record.p_signal[:, 0], dtype=float)
    notes = []
    accepted_rates = _aliases_for('abp-waveform-125hz-mmhg')['rates']
    if record.fs in accepted_rates:
        length = round(len(x) * 124.945 / record.fs)
        x = np.interp(np.linspace(0, len(x) - 1, length), np.arange(len(x)), x)
        notes.append(f'ABP linearly resampled from {record.fs} Hz to 124.945 Hz')
    elif record.fs != 124.945:
        raise Degraded(f'ABP sampling rate {record.fs} Hz is not canonical or declared')
    return dict(kind='waveform', channels={'abp': x}, order=['abp'], rate_hz=124.945,
                units='mmHg', n_samples=len(x), notes=notes)


def _read_ecg_monitor(path, root):
    import numpy as np
    import wfdb
    manifest = _manifest_wfdb(path, root)
    if manifest is None or any(not p.is_file() for p in manifest):
        raise Degraded('monitor ECG requires a complete single-segment WFDB record')
    try:
        record = wfdb.rdrecord(str(path.with_suffix('')))
    except (ValueError, OSError) as exc:
        raise Degraded(f'cannot read monitor ECG: {exc}') from exc
    if not 3 <= record.n_sig <= 5:
        raise Degraded(f'monitor ECG requires three to five leads, got {record.n_sig}')
    channels = {}
    for index, source_name in enumerate(record.sig_name):
        name = str(source_name).strip()
        folded = name.casefold()
        if folded in channels:
            raise Degraded(f'duplicate monitor ECG lead: {name}')
        unit = str(record.units[index]).strip() if index < len(record.units) else ''
        if unit != 'mV':
            raise Degraded(f'monitor ECG lead {name} must use mV, got {unit or "no unit"}')
        channels[folded] = np.asarray(record.p_signal[:, index], dtype=float)
    notes = []
    accepted_rates = _aliases_for('ecg-monitor-3to5lead-250hz-continuous')['rates']
    if record.fs in accepted_rates:
        channels = {
            name: np.interp(np.linspace(0, len(values) - 1,
                                       round(len(values) * 249.89 / record.fs)),
                            np.arange(len(values)), values)
            for name, values in channels.items()
        }
        notes.append(f'monitor ECG linearly resampled from {record.fs} Hz to 249.89 Hz')
    elif record.fs != 249.89:
        raise Degraded(f'monitor ECG sampling rate {record.fs} Hz is not canonical or declared')
    lengths = {len(values) for values in channels.values()}
    if len(lengths) != 1 or not all(lengths):
        raise Degraded('monitor ECG leads must have equal, nonzero lengths')
    return dict(kind='waveform', channels=channels, order=list(channels),
                rate_hz=249.89, units='mV', n_samples=lengths.pop(), notes=notes)


def _read_role_wfdb(path, root, family, roles, units, rate=None):
    """Read only protocol signals after checking every WFDB companion path."""
    import numpy as np
    import wfdb
    if path.suffix.lower() != '.hea' or _manifest_wfdb(path, root) is None:
        raise Degraded('requires a single-segment WFDB header')
    try:
        record = wfdb.rdrecord(str(path.with_suffix('')))
    except (ValueError, OSError, IndexError) as exc:
        raise Degraded(f'cannot read WFDB: {exc}') from exc
    hz = float(record.fs)
    if not math.isfinite(hz) or hz <= 0 or (rate is not None and abs(hz-rate) > 1e-6):
        raise Degraded(f'unexpected sample rate {hz}')
    channels, notes = {}, []
    for index, source in enumerate(record.sig_name):
        role, aliased = _resolve_label(family, source)
        if role not in roles:
            notes.append(f'channel not read: {source}')
            continue
        if role in channels:
            raise Degraded(f'duplicate role: {role}')
        if record.units[index] != units:
            raise Degraded(f'{role} requires {units}')
        channels[role] = np.asarray(record.p_signal[:, index], dtype=float)
        if aliased:
            notes.append(f'{source} read as {role}')
    if not channels or any(not x.size for x in channels.values()):
        raise Degraded('no nonempty protocol signal')
    return dict(kind='waveform', channels=channels, rate_hz=hz, units=units, notes=notes)


def _read_capnography(path, root):
    roles = ('etco2-waveform', 'etco2-scalar', 'transcutaneous')
    if path.suffix.lower() == '.edf':
        return _read_role_edf(path, 'capnography-mmhg', roles, units='mmHg')
    return _read_role_wfdb(path, root, 'capnography-mmhg', roles, 'mmHg')


def _manifest_capnography(path, root):
    return _manifest_one(path, root) if path.suffix.lower() == '.edf' else _manifest_wfdb(path, root)


_PRESSURE_ROLES = ('cvp', 'pap', 'icp')
_PRESSURE_RATE = 124.945


def _read_pressure_nonarterial(path, root):
    """CVP, PAP and ICP by name, in mmHg, at the native 124.945 Hz.

    MIMIC bedside segments store these at two samples per 62.4725 Hz frame; frames
    are expanded, never averaged to the frame rate. Gaps stay NaN and are reported."""
    import numpy as np
    import wfdb
    family = 'pressure-nonarterial-125hz-mmhg'
    if path.suffix.lower() != '.hea' or _manifest_wfdb(path, root) is None:
        raise Degraded('requires a single-segment WFDB header')
    notes, wanted = [], {}
    try:
        header = wfdb.rdheader(str(path.with_suffix('')))
        for index, source in enumerate(header.sig_name):
            role, aliased = _resolve_label(family, source)
            if role not in _PRESSURE_ROLES:
                notes.append(f'channel not read: {source}')
                continue
            if role in wanted:
                raise Degraded(f'duplicate role: {role}')
            wanted[role] = index
            if aliased:
                notes.append(f'{source} read as {role}')
        if not wanted:
            raise Degraded('no CVP, PAP or ICP channel')
        record = wfdb.rdrecord(str(path.with_suffix('')), channels=sorted(wanted.values()),
                               smooth_frames=False)
    except (ValueError, OSError, IndexError) as exc:
        raise Degraded(f'cannot read WFDB: {exc}') from exc
    channels = {}
    for k, source in enumerate(record.sig_name):
        role, _ = _resolve_label(family, source)
        if record.units[k] != 'mmHg':
            raise Degraded(f'{role} requires mmHg')
        hz = float(record.fs) * record.samps_per_frame[k]
        if abs(hz - _PRESSURE_RATE) > 1e-3 * _PRESSURE_RATE:
            raise Degraded(f'{role} sampling rate {hz} Hz is not {_PRESSURE_RATE} Hz')
        x = np.asarray(record.e_p_signal[k], dtype=float)
        if not np.isfinite(x).any():
            raise Degraded(f'{role} has no valid samples')
        missing = float(np.mean(~np.isfinite(x)))
        if missing:
            notes.append(f'{role}: {100 * missing:.1f}% of samples missing')
        channels[role] = x
    return dict(kind='waveform', channels=channels, order=[r for r in _PRESSURE_ROLES if r in channels],
                rate_hz=_PRESSURE_RATE, units='mmHg', notes=notes)


def _read_resp_impedance(path, root):
    return _read_role_wfdb(path, root, 'resp-impedance-62hz-ohm', ('resp',), 'Ohm', 62.4725)
