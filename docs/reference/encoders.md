# Encoders

The model card fields and every encoder in v0.3.0. [Encoders](../learn/perception/encoders.md) explains the encoder folder, images and the check.

## Model card

Contract: model card, `src/medomni/core/contracts/schemas/model-card.schema.json`. One per encoder, at `perception/encoders/<family>/<encoder>/card.yaml`, and published to Hugging Face.

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | `<family>__<name>`, matching the encoder's folder. |
| `family` | yes | The one family it reads. |
| `modality` | yes | The modality, in plain words. |
| `summary` | yes | One sentence on what it does. |
| `authors` | yes | Who built the encoder: name and GitHub handle for each. |
| `intended_use` | no | The population and acquisition it was built for. |
| `limits` | no | Known conditions where it is out of distribution. |
| `outputs` | yes | Each output block's `kind` (`labels`, `events`, `text`, `embedding`), with its `scale`, full `labels` vocabulary or `dim` where relevant. |
| `options` | no | Option name to description. |
| `reliability` | yes | `status` (`unmeasured` or `measured`) and optional `evidence`. |
| `non_training` | yes | Whether it runs zero-shot, with no training on MedOmni data. |
| `license` | yes | License of the code and weights. |
| `source` | yes | `url` and `rev` of the upstream code. |
| `weights` | no | `uri` and `sha256` of the weights. |
| `runtime` | no | `image` and `digest` of the container. |
| `acceptance` | yes | `pending` or `accepted`, set by review. |

A model card has no extra keys, its family exists, and an encoder never returns a label outside its declared vocabulary.

## Encoders in v0.3.0

44 encoders. Each is built as an image on your machine with `medomni perception check`; see [Check and freeze](../learn/perception/encoders.md#check-and-freeze).

Licenses differ. Some are non-commercial (CC BY-NC) or copyleft (GPL); read the model card before using an encoder outside research.

| Encoder | Family | License |
|---|---|---|
| `body-position-code-10hz__rule-occupancy` | `body-position-code-10hz` | Apache-2.0 |
| `cgm-5min-mgdl__pyagata` | `cgm-5min-mgdl` | GPL-3.0-only |
| `clinical-measurement-irregular__labs-summary` | `clinical-measurement-irregular` | Apache-2.0 |
| `cxr-radiograph-2d__biomedclip` | `cxr-radiograph-2d` | MIT |
| `cxr-radiograph-2d__chexzero` | `cxr-radiograph-2d` | MIT |
| `cxr-radiograph-2d__torchxrayvision` | `cxr-radiograph-2d` | Apache-2.0 |
| `ecg-12lead-500hz-mv__ecgfounder` | `ecg-12lead-500hz-mv` | MIT |
| `ecg-1lead-200hz-uv__ecgfounder` | `ecg-1lead-200hz-uv` | MIT |
| `ecg-1lead-200hz-uv__neurokit2` | `ecg-1lead-200hz-uv` | MIT |
| `ecg-monitor-3to5lead-250hz-continuous__ecgfounder` | `ecg-monitor-3to5lead-250hz-continuous` | MIT |
| `eeg-sleep-6ch-200hz-uv__yasa` | `eeg-sleep-6ch-200hz-uv` | BSD-3-Clause |
| `emg-chin-200hz-uv__rule-amplitude` | `emg-chin-200hz-uv` | Apache-2.0 |
| `emg-limb-200hz-uv__rule-amplitude` | `emg-limb-200hz-uv` | Apache-2.0 |
| `eog-2ch-200hz-uv__wav2sleep-eog` | `eog-2ch-200hz-uv` | MIT |
| `flio-tcspc-256x256x1024bin-u16__rule-photons` | `flio-tcspc-256x256x1024bin-u16` | Apache-2.0 |
| `fundus-faf-mono8-2d__retinograd` | `fundus-faf-mono8-2d` | MIT |
| `fundus-faf-mono8-2d__rule-intensity` | `fundus-faf-mono8-2d` | Apache-2.0 |
| `fundus-photography-2d__dr-grade` | `fundus-photography-2d` | MIT |
| `fundus-photography-2d__retfound` | `fundus-photography-2d` | CC-BY-NC-4.0 |
| `fundus-photography-2d__retfound-dr` | `fundus-photography-2d` | CC-BY-NC-4.0 |
| `fundus-photography-2d__retfound-jsiec` | `fundus-photography-2d` | CC-BY-NC-4.0 |
| `oct-bscanset-radial24-circle3-mono8__mirage-onh` | `oct-bscanset-radial24-circle3-mono8` | CC-BY-NC-ND-4.0 |
| `oct-bscanset-radial24-circle3-mono8__rule-intensity` | `oct-bscanset-radial24-circle3-mono8` | Apache-2.0 |
| `oct-volume-raster-mono8-3d__kdoct` | `oct-volume-raster-mono8-3d` | MIT |
| `oct-volume-raster-mono8-3d__mirage` | `oct-volume-raster-mono8-3d` | CC-BY-NC-ND-4.0 |
| `oct-volume-raster-mono8-3d__rule-intensity` | `oct-volume-raster-mono8-3d` | Apache-2.0 |
| `octa-enface-slab-mono8-2d__rule-intensity` | `octa-enface-slab-mono8-2d` | Apache-2.0 |
| `octa-enface-slab-mono8-2d__vessel-density` | `octa-enface-slab-mono8-2d` | Apache-2.0 |
| `octa-flowcube-mono8-3d__flow-metrics` | `octa-flowcube-mono8-3d` | Apache-2.0 |
| `octa-flowcube-mono8-3d__rule-intensity` | `octa-flowcube-mono8-3d` | Apache-2.0 |
| `ppg-waveform-uncal__bayesbeat` | `ppg-waveform-uncal` | UNDECLARED |
| `ppg-waveform-uncal__neurokit2` | `ppg-waveform-uncal` | MIT |
| `pressure-nonarterial-125hz-mmhg__rule-summary` | `pressure-nonarterial-125hz-mmhg` | Apache-2.0 |
| `psg-cardiorespiratory-4ch-200hz-mixed__wav2sleep` | `psg-cardiorespiratory-4ch-200hz-mixed` | MIT |
| `pulse-rate-10hz-bpm__rule-summary` | `pulse-rate-10hz-bpm` | Apache-2.0 |
| `resp-effort-rip-2ch-50hz__neurokit2` | `resp-effort-rip-2ch-50hz` | MIT |
| `resp-flow__rule-amplitude` | `resp-flow` | Apache-2.0 |
| `resp-impedance-62hz-ohm__rule-amplitude` | `resp-impedance-62hz-ohm` | Apache-2.0 |
| `retinal-heightmap-surfaces-f32__layer-thickness` | `retinal-heightmap-surfaces-f32` | Apache-2.0 |
| `retinal-heightmap-surfaces-f32__rule-surfaces` | `retinal-heightmap-surfaces-f32` | Apache-2.0 |
| `snore-acoustic__rule-amplitude` | `snore-acoustic` | Apache-2.0 |
| `spo2-series-10hz-pct__pobm` | `spo2-series-10hz-pct` | GPL-3.0 |
| `wearable-hr-1min-bpm__rule-summary` | `wearable-hr-1min-bpm` | Apache-2.0 |
| `wearable-spo2-1min-pct__rule-summary` | `wearable-spo2-1min-pct` | Apache-2.0 |

## Where next

- [Use the encoders](../guides/use-the-encoders.md): pull an image and call it.
- [Gateway API](gateway-api.md): how cards and evidence are served.
- [Families](families.md): the input each family expects.
