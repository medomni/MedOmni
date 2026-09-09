# Fixtures

`input.edf` is an authored signal for repeatable pipeline checks, not a patient recording.
It contains six 200 Hz channels in microvolts for five minutes.
Each channel is a sum of 2 Hz and 10 Hz sinusoids, with a channel-specific phase.
The frozen stages verify deterministic inference, not sleep-stage accuracy.

Local checks also use authorized MedOmni/family-samples EEG samples 01 and 03.
These BDSP excerpts cover separate mastoid electrodes and explicit A1/A2 references.
Restricted patient recordings are not included in this repository or image.

## Published sleep example

`input-physionet.edf` contains seconds 360 through 960 (end exclusive) from record tr03-0005 of PhysioNet/CinC Challenge 2018, version 1.0.0.
Source: https://physionet.org/content/challenge-2018/1.0.0/
Source directory: `training/tr03-0005/`; files `.hea`, `.mat`, and `.arousal`.
Citation: Ghassemi et al. (2018), You Snooze, You Win: the PhysioNet/Computing in Cardiology Challenge 2018, DOI 10.22489/CinC.2018.049.
Contains information from this dataset, made available under the ODC Attribution License 1.0:
https://physionet.org/content/challenge-2018/view-license/1.0.0/
This derived fixture and reference annotations retain that license.

The six named EEG channels are preserved at 200 Hz in microvolts.
WFDB physical samples are written to EDF with unit gain and the signed 16-bit range.
A read-back comparison confirmed exact equality of every retained sample. No filtering or resampling occurs.
The EDF header is newly generated and does not assert patient identity or acquisition date.
Only the first 4,992,024 source MAT bytes are needed: its 24-byte header plus 960 seconds of 13-channel samples.
SHA-256 of that downloaded prefix: `1acb02e712fb582ddda49be15a5105f32580ca33a9ef50d1a7537832d810c8c5`.
Source header SHA-256: `c1f61e772f2bcd53910111bc87f20367df08b0fb701aba64920dace3e0d34b4b`.
Source annotations SHA-256: `aba4cc9495098a249eac8339aafc698f328912e2f37206e3e44cfb9f189575fd`.

`reference-stages.json` contains 20 clinician-labelled epochs derived from `.arousal` stage transitions.
Times are seconds relative to the excerpt. W becomes Wake and R becomes REM; the other stage names are unchanged.
These reference labels are independent of YASA. Frozen model output is not clinical ground truth and need not match every epoch.
