# Contributors

MedOmni is built by the people below. The public history keeps each person's commits on the files that exist today; the work listed here also covers files that v0.3 replaced or removed, whose history isn't published.

- **Bosong Huang**: MedOmni's design and most of its code: Core, Bench, Perception's gateway and runtime, Studio, the task builder, the datasets and their tasks, the evaluation protocol, the docs, and the v0.2 benchmark this release grew from.
- **Timo Stoffregen**: Perception's encoder containers: ECGFounder, NeuroKit2 (ECG, respiratory effort, PPG), POBM (SpO2), PyVital (arterial pressure), CheXzero and BiomedCLIP (chest X-ray), ICLabel, EventNet, NeuroGNN and the Zhu EEG transformer, yasa and wav2sleep for sleep, and others; the encoder registry and runtime they run on; and the family aliases.
- **Nicolas Zumarraga**: Perception's rule-based encoders across many families (body position, pulse rate, respiratory flow and impedance, snore, capnography, actigraphy, the retinal OCT, OCTA, FAF and FLIO families, the retinal heightmaps), and parts of the gateway.
- **Xianglong Bao**: the retinal imaging encoders: diabetic retinopathy grading, the optic-nerve-head B-scan set, OCTA flow-cube measurement, OCT volume embedding and fundus autofluorescence gradability.
- **Xiaoda Wang**: the v0.2 audit matrix (shared matrix layer, reviews as signatures) and fixes to how judged runs are read, which Studio's audit carries forward.
