# Published test data

Source: [Siena Scalp EEG 1.0.0](https://physionet.org/content/siena-scalp-eeg/1.0.0/). Detti, Vatti and Zabalo Manrique de Lara, 2020.

License: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Retain attribution and license notices with these excerpts.

PN00-1.edf excerpts [1040,1280) and [300,540) seconds. Select the 19 named electrodes from EDF headers, preserving the recorded reference. Resample 512 to 200 Hz with scipy.signal.resample_poly(up=25, down=64). Store in EDF microvolts. Published seizure onset and end map to 103 and 173 seconds in input.edf. The flat fixture is an authored rejection case. No artifact-component labels are provided.

Source SHA-256:

- `Seizures-list-PN00.txt`: `a5bf9d78e67d4ef6f640e06b443e409ea724e8a7da7c318b40bae476cf150d43`
- `PN00-1.edf`: `d8b1fdbc7f71feb788e9cce4169c0637579ff1cc9f5d03aa88d3c4d708e72eed`

Fixture SHA-256:

- `input-background.edf`: `0276ac79d059d87b209cef443be39c461e126ef4ffd65fea0c2d7d6635398630`
- `input-flat.edf`: `7d97d76438b5403053e3560b7febb8fde86e7ab21437eb1e507748edb66a57b3`
- `input.edf`: `1fbcbb8f84c155593ee88aa4138bbac365732fe37c2ecb668e5a58dac4ecce0e`
