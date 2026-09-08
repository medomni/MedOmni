# Fixtures

`input.edf` is an authored signal for repeatable pipeline checks, not a patient recording.
It contains six 200 Hz channels in microvolts for five minutes.
Each channel is a sum of 2 Hz and 10 Hz sinusoids, with a channel-specific phase.
The frozen stages verify deterministic inference, not sleep-stage accuracy.

Local checks also use authorized MedOmni/family-samples EEG samples 01 and 03.
These BDSP excerpts cover separate mastoid electrodes and explicit A1/A2 references.
Restricted patient recordings are not included in this repository or image.
