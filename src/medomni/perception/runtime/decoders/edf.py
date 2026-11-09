"""Decoders for families stored as EDF."""
import math

from ..aliases import _aliases_for, _normalize_label, _resolve_label
from ._util import _confined_companion, _edf_signals, _read_json_manifest
from ..errors import Degraded

_SLEEP_CHANNELS = ('f3-m2', 'f4-m1', 'c3-m2', 'c4-m1', 'o1-m2', 'o2-m1')


def _read_sleep_edf(path, root):
    import numpy as np
    signals = {}
    used_aliases = []
    for signal in _edf_signals(path):
        name, resolved = _resolve_label('eeg-sleep-6ch-200hz-uv', signal.label)
        if name in signals:
            raise Degraded(f'duplicate EEG channel: {name}')
        signals[name] = signal
        if resolved:
            used_aliases.append(f'{signal.label.strip()} read as {name}')
    channels, notes = {}, used_aliases
    def values(name):
        signal = signals[name]
        if signal.sampling_frequency != 200 or signal.physical_dimension not in ('uV', 'µV', 'μV'):
            raise Degraded(f'{name} must be sampled at 200 Hz in microvolts')
        return np.asarray(signal.data, dtype=float)
    for name in _SLEEP_CHANNELS:
        if name in signals:
            channels[name] = values(name)
        else:
            electrode, reference = name.split('-')
            if electrode not in signals or reference not in signals:
                raise Degraded(f'missing EEG derivation: {name}')
            left, right = values(electrode), values(reference)
            if left.shape != right.shape:
                raise Degraded(f'unequal electrode lengths for {name}')
            channels[name] = left - right
            notes.append(f'{name} derived by subtracting the mastoid reference')
    lengths = {len(v) for v in channels.values()}
    if len(lengths) != 1:
        raise Degraded('EEG channel lengths differ')
    return {'kind': 'waveform', 'channels': channels, 'order': list(_SLEEP_CHANNELS),
            'rate_hz': 200., 'units': 'uV', 'n_samples': lengths.pop(), 'notes': notes}


def _read_named_edf(path, family, names, rate, units):
    """Read a declared set of channels without resampling or filling missing data."""
    import numpy as np
    selected = {}
    used_aliases = []
    extra = []
    for signal in _edf_signals(path):
        source_name = _normalize_label(signal.label)
        name, resolved = _resolve_label(family, signal.label)
        if name not in names:
            extra.append(signal.label)
            continue
        if name in selected:
            raise Degraded(f'duplicate channel: {name}')
        if signal.sampling_frequency != rate:
            raise Degraded(f'{name} must be sampled at {rate} Hz')
        accepted = ('uV', 'µV', 'μV') if units == 'uV' else (units,)
        if units is not None and signal.physical_dimension not in accepted:
            raise Degraded(f'{name} must use {units}')
        selected[name] = np.asarray(signal.data, dtype=float)
        if resolved:
            used_aliases.append(f'{source_name} read as {name}')
    missing = set(names) - selected.keys()
    if missing:
        raise Degraded('missing channels: ' + ', '.join(sorted(missing)))
    lengths = {len(x) for x in selected.values()}
    if len(lengths) != 1 or not all(lengths):
        raise Degraded('channels must have equal, nonzero lengths')
    notes = used_aliases
    if extra:
        notes.append('channels not read: ' + ', '.join(extra))
    return dict(kind='waveform', channels=selected, order=list(names), rate_hz=float(rate),
                units=units, n_samples=lengths.pop(), notes=notes)



def _read_ecg_single(path, root):
    return _read_named_edf(path, 'ecg-1lead-200hz-uv', ('ecg',), 200, 'uV')


def _read_eog(path, root):
    return _read_named_edf(path, 'eog-2ch-200hz-uv', ('e1-m2', 'e2-m1'), 200, 'uV')



def _read_rip(path, root):
    return _read_named_edf(path, 'resp-effort-rip-2ch-50hz',
                           ('thorax', 'abdomen'), 50, None)



def _read_spo2(path, root):
    return _read_named_edf(path, 'spo2-series-10hz-pct', ('spo2',), 10, '%')


_CARDIO_PSG_CHANNELS = ('ecg', 'pleth', 'abd', 'thx')


def _read_cardio_psg(path, root):
    import numpy as np
    family = 'psg-cardiorespiratory-4ch-200hz-mixed'
    aliases = _aliases_for(family)
    selected, dimensions, notes = {}, {}, []
    for signal in _edf_signals(path):
        source = _normalize_label(signal.label)
        name, resolved = _resolve_label(family, signal.label)
        if name not in _CARDIO_PSG_CHANNELS:
            continue
        if name in selected:
            raise Degraded(f'duplicate cardiorespiratory channel: {name}')
        rate = float(signal.sampling_frequency)
        if rate != 200 and rate not in aliases['rates']:
            raise Degraded(f'{name} must be sampled at 200 Hz')
        values = np.asarray(signal.data, dtype=float)
        if rate != 200:
            length = round(len(values) * 200 / rate)
            values = np.interp(np.linspace(0, len(values) - 1, length),
                               np.arange(len(values)), values)
            notes.append(f'{name} linearly resampled from {rate:g} Hz to 200 Hz')
        selected[name] = values
        dimensions[name] = signal.physical_dimension or None
        if resolved:
            notes.append(f'{source} read as {name}')
    missing = set(_CARDIO_PSG_CHANNELS) - selected.keys()
    if missing:
        raise Degraded('missing cardiorespiratory channels: ' + ', '.join(sorted(missing)))
    lengths = {len(values) for values in selected.values()}
    if len(lengths) != 1 or not all(lengths):
        raise Degraded('cardiorespiratory channels must have equal, nonzero lengths')
    return dict(kind='waveform', channels=selected, order=list(_CARDIO_PSG_CHANNELS),
                rate_hz=200.0, units=dimensions, n_samples=lengths.pop(), notes=notes)


def _read_brain_age(path, root):
    return _read_named_edf(path, 'eeg-n2-bipolar-2ch-250hz-uv',
                           ('f4-c4', 'c4-o2'), 250, 'uV')


def _read_hfo_event(path, root):
    import numpy as np
    import edfio
    manifest = _read_json_manifest(path, root)
    target = _confined_companion(path, root, manifest.get('file'))
    channel = manifest.get('channel')
    start, end = manifest.get('start_sec'), manifest.get('end_sec')
    if (not isinstance(channel, str) or not channel
            or isinstance(start, bool) or not isinstance(start, (int, float))
            or isinstance(end, bool) or not isinstance(end, (int, float))
            or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end):
        raise Degraded('HFO manifest needs channel and a valid start_sec/end_sec interval')
    try:
        record = edfio.read_edf(target)
    except (OSError, ValueError) as exc:
        raise Degraded(f'cannot read HFO EDF: {exc}') from exc
    matches = [signal for signal in record.signals
               if signal.label.strip().casefold() == channel.strip().casefold()]
    if len(matches) != 1:
        raise Degraded(f'HFO channel must occur once: {channel}')
    signal = matches[0]
    if signal.sampling_frequency != 2000:
        raise Degraded(f'HFO signal must be sampled at 2000 Hz, got {signal.sampling_frequency}')
    if signal.physical_dimension not in ('uV', 'µV', 'μV'):
        raise Degraded('HFO signal must use microvolts')
    first, last = round(start * 2000), round(end * 2000)
    values = np.asarray(signal.data[first:last], dtype=float)
    if len(values) < 40 or not np.isfinite(values).all() or np.ptp(values) == 0:
        raise Degraded('HFO event is too short, non-finite, or flat')
    return dict(kind='hfo-event', waveform=values, rate_hz=2000.0, units='uV',
                channel=channel, start_sec=float(start), end_sec=float(end), notes=[])



_SCALP_CHANNELS = ('fp1', 'fp2', 'f3', 'f4', 'c3', 'c4', 'p3', 'p4', 'o1', 'o2',
                   'f7', 'f8', 't3', 't4', 't5', 't6', 'fz', 'cz', 'pz')



def _read_scalp(path, root):
    return _read_named_edf(path, 'eeg-scalp-1020-19ch-200hz-uv',
                           _SCALP_CHANNELS, 200, 'uV')


def _read_emg_chin(path, root):
    return _read_named_edf(path, 'emg-chin-200hz-uv', ('chin1-chin2',), 200, 'uV')


def _read_role_edf(path, family, roles, rate=None, units=None):
    """Read available protocol roles; retain each channel's rate and physical unit."""
    import numpy as np
    channels, rates, channel_units, notes = {}, {}, {}, []
    for signal in _edf_signals(path):
        role, aliased = _resolve_label(family, signal.label)
        if role not in roles:
            notes.append(f'channel not read: {signal.label}')
            continue
        if role in channels:
            raise Degraded(f'duplicate role: {role}')
        hz = float(signal.sampling_frequency)
        if not math.isfinite(hz) or hz <= 0 or (rate is not None and hz != rate):
            raise Degraded(f'{role}: unexpected sampling rate {hz}')
        unit = signal.physical_dimension
        accepted = ('uV', 'µV', 'μV') if units == 'uV' else (units,)
        if units is not None and unit not in accepted:
            raise Degraded(f'{role} requires {units}')
        channels[role] = np.asarray(signal.data, dtype=float)
        rates[role] = hz
        channel_units[role] = units if units is not None else (unit or None)
        if aliased:
            notes.append(f'{signal.label} read as {role}')
    if not channels or any(not x.size for x in channels.values()):
        raise Degraded('no nonempty protocol signal')
    return dict(kind='waveform', channels=channels, rates=rates,
                channel_units=channel_units, notes=notes)


def _read_emg_limb(path, root):
    return _read_role_edf(path, 'emg-limb-200hz-uv',
                          ('leg-left', 'leg-right', 'arm-left', 'arm-right'), 200, 'uV')


def _read_resp_flow(path, root):
    return _read_role_edf(path, 'resp-flow', ["nasal-pressure","derived-flow","thermistor"])


def _read_snore(path, root):
    return _read_role_edf(path, 'snore-acoustic', ["snore","snoring-sensor"])


def _read_pulse_rate(path, root):
    return _read_named_edf(path, 'pulse-rate-10hz-bpm', ('pulse',), 10, 'bpm')


def _read_body_position(path, root):
    return _read_named_edf(path, 'body-position-code-10hz', ('position',), 10, None)


def _read_actigraphy(path, root):
    return _read_role_edf(path, 'actigraphy-gravity-10hz',
                          ('gravity-x', 'gravity-y', 'activity', 'elevation'), 10)
