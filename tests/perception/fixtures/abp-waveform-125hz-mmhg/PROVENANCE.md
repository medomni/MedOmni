# Published test data

Source: [MGH/MF Waveform Database 1.0.0](https://physionet.org/content/mghdb/1.0.0/). Welch et al., 1991.

License: ODC-By 1.0 (https://opendatacommons.org/licenses/by/1-0/). Retain attribution and license notices with these excerpts.

Resample the complete ART channel from record mgh001 with scipy.signal.resample_poly(up=24989, down=72000), from 360 to 124.945 Hz. Then select 3750 samples starting at index 89960 (719.9967985913803 seconds). Resampling before cropping avoids artificial filter transients at excerpt boundaries. Preserve mmHg in 16-bit WFDB. The constant-pressure fixture is an authored rejection case. No reference HPI score exists.

Source SHA-256:

- `mgh001.hea`: `d49b39186262549b99129c8ebcb7ddfbdc66e14ef69586dd9a041cfaa879d6ea`
- `mgh001.dat`: `07059d20fc4042eb861e067dd0aadc71f174adc7c832600ed149b702eca2629e`

Fixture SHA-256:

- `input-flat.hea`: `2fd359179ff9c36baf76809988c77fb3e223fa2358588aa58fb097ea3c69b10a`
- `input.hea`: `ec4dbb8efb12ae63edf49b22fc2bb2b6e27bcd00b62af63eee882a86d91dc7c3`
