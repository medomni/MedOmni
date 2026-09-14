# Lab fixtures

`input.jsonl` is an authored example of the task builder's lab and vital-sign row formats. It contains no patient data.
The fixture is covered by this repository's license.

The two mg/dL creatinine values have count 2, minimum 1.0, maximum 1.4, mean 1.2, and latest value 1.4.
The 110 umol/L value forms a separate group. The vital-sign row is excluded with a note.
These hand-derived results provide the independent baseline. The published example below checks real clinical input.

## Published lab example

`input-mimic-demo.jsonl` contains 154 numeric lab results from the first 24 hours of admission 20044587 in MIMIC-IV Clinical Database Demo 2.2.
The interval begins at the admission's earliest lab timestamp, 2113-08-25T07:29:00.
Selection uses the lowest numeric nonempty admission ID, then sorts by charttime and labevent_id.
`valuenum` becomes value; `valueuom` becomes unit; labels come from d_labitems.
The deidentified timestamps, numeric values, and item IDs are unchanged. Patient identifiers and free text are omitted.
Rows without a finite valuenum are excluded; no measurement is imputed.

Source: https://physionet.org/content/mimic-iv-demo/2.2/
Files: `hosp/labevents.csv.gz` and `hosp/d_labitems.csv.gz`.
Citation: Johnson et al. (2023), MIMIC-IV Clinical Database Demo 2.2, DOI 10.13026/dp1f-ex47.
This derived lab fixture is available under ODbL 1.0; see LICENSE-MIMIC-DEMO.txt.
Source SHA-256: labevents `d51a4cf1ea63245abe7d544b0d50a928e9ee2ec5eb9a5ce85500aed0bd6c6dfc`; d_labitems `72ea5f020469fd24543bd98ab3bd0a4f645a5a4b7802d9d52af20d736f9d76db`.
