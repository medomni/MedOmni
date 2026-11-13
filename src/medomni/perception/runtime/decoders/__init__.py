"""One decoder per family: bytes in, a decoded sample out (Container API).

The decoders are Perception's; which labels, rates, prefixes and colour modes a family accepts comes from Core's
families module (`aliases.py`). Each reader takes (path, root): only readers that follow references to other files
need root, so those names are confined too. A family's channel names are still repeated in its decoder; they match
Core's family files."""
import os
from pathlib import Path

from ._util import _manifest_json_files, _manifest_one, _manifest_wfdb
from .edf import _read_actigraphy, _read_body_position, _read_brain_age, _read_cardio_psg, _read_ecg_single, _read_emg_chin, _read_emg_limb, _read_eog, _read_hfo_event, _read_pulse_rate, _read_resp_flow, _read_rip, _read_scalp, _read_sleep_edf, _read_snore, _read_spo2
from .images import _read_echo_frame, _read_echo_study, _read_flio, _read_fundus_dicom, _read_fundus_faf, _read_image, _read_oct_radial, _read_oct_raster, _read_octa_enface, _read_octa_flowcube, _read_retinal_heightmap
from .tables import _read_cgm, _read_measurements, _read_numeric_observations, _read_wearable_hr, _read_wearable_resp, _read_wearable_spo2
from .wfdb_ import _manifest_capnography, _manifest_ppg, _read_abp, _read_capnography, _read_ecg_monitor, _read_ppg, _read_pressure_nonarterial, _read_resp_impedance, _read_wfdb_12lead
from ..errors import BadRequest


_READERS = {
    'retinal-heightmap-surfaces-f32': _read_retinal_heightmap,
    'flio-tcspc-256x256x1024bin-u16': _read_flio,
    'fundus-faf-mono8-2d': _read_fundus_faf,
    'oct-bscanset-radial24-circle3-mono8': _read_oct_radial,
    'octa-flowcube-mono8-3d': _read_octa_flowcube,
    'octa-enface-slab-mono8-2d': _read_octa_enface,
    'oct-volume-raster-mono8-3d': _read_oct_raster,
    'resp-impedance-62hz-ohm': _read_resp_impedance,
    'capnography-mmhg': _read_capnography,
    'actigraphy-gravity-10hz': _read_actigraphy,
    'body-position-code-10hz': _read_body_position,
    'pulse-rate-10hz-bpm': _read_pulse_rate,
    'snore-acoustic': _read_snore,
    'resp-flow': _read_resp_flow,
    'emg-limb-200hz-uv': _read_emg_limb,
    'emg-chin-200hz-uv': _read_emg_chin,
    'wearable-spo2-1min-pct': _read_wearable_spo2,
    'wearable-resprate-1min-brpm': _read_wearable_resp,
    'wearable-hr-1min-bpm': _read_wearable_hr,
    'psg-cardiorespiratory-4ch-200hz-mixed': _read_cardio_psg,
    'eog-2ch-200hz-uv': _read_eog,
    'eeg-n2-bipolar-2ch-250hz-uv': _read_brain_age,
    'ecg-monitor-3to5lead-250hz-continuous': _read_ecg_monitor,
    'numeric-observation': _read_numeric_observations,
    'echo-study-dicom-video': _read_echo_study,
    'echo-ultrasound-frame-2d': _read_echo_frame,
    'ieeg-hfo-event-2khz-uv': _read_hfo_event,
    'eeg-scalp-1020-19ch-200hz-uv': _read_scalp,
    'abp-waveform-125hz-mmhg': _read_abp,
    'pressure-nonarterial-125hz-mmhg': _read_pressure_nonarterial,
    'spo2-series-10hz-pct': _read_spo2,
    'resp-effort-rip-2ch-50hz': _read_rip,
    'ecg-1lead-200hz-uv': _read_ecg_single,
    "fundus-photography-2d": _read_fundus_dicom,
    "ppg-waveform-uncal": _read_ppg,
    "eeg-sleep-6ch-200hz-uv": _read_sleep_edf,
    "cgm-5min-mgdl": _read_cgm,
    "clinical-measurement-irregular": _read_measurements,
    "cxr-radiograph-2d": _read_image,
    "ecg-12lead-500hz-mv": _read_wfdb_12lead,
}

_MANIFESTS = {
    'retinal-heightmap-surfaces-f32': _manifest_one,
    'flio-tcspc-256x256x1024bin-u16': _manifest_one,
    'fundus-faf-mono8-2d': _manifest_one,
    'oct-bscanset-radial24-circle3-mono8': _manifest_one,
    'octa-flowcube-mono8-3d': _manifest_one,
    'octa-enface-slab-mono8-2d': _manifest_one,
    'oct-volume-raster-mono8-3d': _manifest_one,
    'resp-impedance-62hz-ohm': _manifest_wfdb,
    'capnography-mmhg': _manifest_capnography,
    'actigraphy-gravity-10hz': _manifest_one,
    'body-position-code-10hz': _manifest_one,
    'pulse-rate-10hz-bpm': _manifest_one,
    'snore-acoustic': _manifest_one,
    'resp-flow': _manifest_one,
    'emg-limb-200hz-uv': _manifest_one,
    'emg-chin-200hz-uv': _manifest_one,
    'wearable-spo2-1min-pct': _manifest_one,
    'wearable-resprate-1min-brpm': _manifest_one,
    'wearable-hr-1min-bpm': _manifest_one,
    'psg-cardiorespiratory-4ch-200hz-mixed': _manifest_one,
    'eog-2ch-200hz-uv': _manifest_one,
    'eeg-n2-bipolar-2ch-250hz-uv': _manifest_one,
    'ecg-monitor-3to5lead-250hz-continuous': _manifest_wfdb,
    'numeric-observation': _manifest_one,
    'echo-study-dicom-video': _manifest_json_files,
    'echo-ultrasound-frame-2d': _manifest_one,
    'ieeg-hfo-event-2khz-uv': _manifest_json_files,
    'eeg-scalp-1020-19ch-200hz-uv': _manifest_one,
    'abp-waveform-125hz-mmhg': _manifest_wfdb,
    'pressure-nonarterial-125hz-mmhg': _manifest_wfdb,
    'spo2-series-10hz-pct': _manifest_one,
    'resp-effort-rip-2ch-50hz': _manifest_one,
    'ecg-1lead-200hz-uv': _manifest_one,
    "fundus-photography-2d": _manifest_one,
    "ppg-waveform-uncal": _manifest_ppg,
    "eeg-sleep-6ch-200hz-uv": _manifest_one,
    "cgm-5min-mgdl": _manifest_one,
    "clinical-measurement-irregular": _manifest_one,
    "cxr-radiograph-2d": _manifest_one,
    "ecg-12lead-500hz-mv": _manifest_wfdb,
}


def input_manifest(family, path, data_root=None):
    """Every file this input is made of, or None when the family cannot say."""
    manifest = _MANIFESTS.get(family)
    if manifest is None:
        return None
    root = Path(data_root or os.environ.get("DATA_ROOT", "/data")).resolve()
    return manifest(Path(path), root)


def read_family(family, path, data_root=None):
    """Bytes -> a decoded sample. Fails loudly for a family with no decoder."""
    reader = _READERS.get(family)
    if reader is None:
        raise BadRequest(f"no decoder for family '{family}'")
    root = Path(data_root or os.environ.get("DATA_ROOT", "/data")).resolve()
    return reader(path, root)
