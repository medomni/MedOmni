## Data

Everything staged for this patient is under `/workspace/data/`. The record is organised by *family*: a family is one named kind of input in one fixed format — for example the six-channel sleep EEG as an EDF file (`eeg-sleep-6ch-200hz-uv`), or coded clinical records as CSV tables (`clinical-record-table`).{encoder_sentence}

{family_list}

This is the patient's whole record up to the prediction time, not a curated subset. Deciding which inputs matter is part of the task.
