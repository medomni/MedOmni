# Test data provenance

Every sample this encoder is tested against: where it comes from, and what its
license permits.

## The three samples

All three are real twelve-lead ECGs from PTB-XL, at 500 Hz, ten seconds long —
exactly the input this checkpoint declares. Each was chosen because it carries a
finding the card declares, so a reader can tell a working container from a broken
one by looking at the response.

| File | PTB-XL `ecg_id` | PTB-XL statement | Report (German, as published) |
|---|---|---|---|
| `input-ptbxl-00057.hea` | 57 | `NORM` | *sinusrhythmus normales ekg* |
| `input-ptbxl-08215.hea` | 8215 | `AFIB` | *normokardes vorhofflimmern, linkstyp* |
| `input-ptbxl-01737.hea` | 1737 | `IMI` | *sinusrhythmus linkstyp, inferiorer infarkt, chronisch, sicher* |

All three are human-validated (`validated_by_human`), carry no noise or
electrode-problem flag, and sit in PTB-XL's official held-out split
(`strat_fold` 10).

| Field | Value |
|---|---|
| Dataset | PTB-XL, a large publicly available electrocardiography dataset, v1.0.3 |
| Obtained from | https://physionet.org/content/ptb-xl/1.0.3/ |
| Format | WFDB, 16-bit at 1 µV/LSB, 500 Hz, 12 leads, 10 seconds |
| License | Creative Commons Attribution 4.0 International |

**License.** CC BY 4.0 permits redistribution, including inside a container
image, and asks for attribution and a link to the license. Both are here, and
the citation the dataset asks for is below.

    Wagner, P., Strodthoff, N., Bousseljot, R., Samek, W., & Schaeffter, T.
    (2022). PTB-XL, a large publicly available electrocardiography dataset
    (version 1.0.3). PhysioNet. https://doi.org/10.13026/kfzx-aw45

    Wagner, P., Strodthoff, N., Bousseljot, RD., Kreiseler, D., Lunze, F.I.,
    Samek, W., Schaeffter, T. (2020), PTB-XL: A Large Publicly Available ECG
    Dataset. Scientific Data. https://doi.org/10.1038/s41597-020-0495-6

    License: https://creativecommons.org/licenses/by/4.0/

## What was changed, and what was not

`fetch_input.py` downloads each record and checks it against the sha256 that
PhysioNet publishes in the dataset's own `SHA256SUMS.txt`. It then renames two
things and rewrites two fields. Nothing else.

**The signal files are byte-identical to the published `.dat`**, and keep the
published sha256:

| File here | Published as | sha256 |
|---|---|---|
| `ptbxl-00057.dat` | `records500/00000/00057_hr.dat` | `1339a5f8000982272f0e49893506baeafb357994a171b665198d67c84b873870` |
| `ptbxl-01737.dat` | `records500/01000/01737_hr.dat` | `5a4c21d08db31b5b6c72fd0242583994e53b50088e4ab2ec149717c1f241e711` |
| `ptbxl-08215.dat` | `records500/08000/08215_hr.dat` | `58639475a1b1c36a2c5ee3cb4ce68cc872e7e85521324f9b691b7c215d4d84f4` |

**The headers are rewritten in two fields**: the record name on line 1, and the
file name that begins each signal line. Gains, baselines, lead names and the
per-signal checksums are untouched, because the samples are untouched.

Why rename at all: a WFDB record is two files, and the test harness treats every
`input*` file in this directory as one sample. A signal file is not a sample, it
is half of one. So the header carries the `input-` prefix and the signal file
does not, and `registry.py test` sends three requests rather than six.

## What these responses do and do not show

The container answers each record in about 130 ms on CPU. On the first two, the
top statements are the ones the record was labelled with:

| File | Top statements |
|---|---|
| `input-ptbxl-00057.hea` | SINUS RHYTHM 0.999, NORMAL SINUS RHYTHM 0.998, NORMAL ECG 0.989 |
| `input-ptbxl-08215.hea` | ATRIAL FIBRILLATION 0.963, ABNORMAL ECG 0.951 |

**On the third it is confidently abnormal and wrong about where.** Record 1737 is
a chronic *inferior* infarct. The encoder returns ABNORMAL ECG 0.999 and NORMAL
ECG 0.016, so it is not fooled about whether the recording is abnormal. But it
puts the infarct in the wrong wall: SEPTAL INFARCT 0.279 and ANTEROSEPTAL INFARCT
0.194, against INFERIOR INFARCT 0.039. It also gives LEFT AXIS DEVIATION only
0.126, where the report says *linkstyp*.

That is recorded here rather than left out, because it is the point of using real
data. Three records measure nothing — `expected.json` freezes this encoder's
output so a change of behavior is caught, and it is not a validation. Reliability
stays `unmeasured` on the card until somebody measures it.

## Why these are out of sample

ECGFounder was pretrained on the Harvard-Emory ECG Database, over ten million
recordings. PTB-XL is not part of that, so these three records are out of sample
for this checkpoint. Upstream's own `ptbxl_eval.py` uses PTB-XL as an external
evaluation set for the same reason.

This is the opposite of the situation on the torchxrayvision card, whose weights
were trained on MIMIC-CXR among others. Neither fact is a verdict on either
encoder; both belong on the record.

## What is not here, and why

No MIMIC-ECG record. MIMIC is under the PhysioNet credentialed license, which
does not permit redistribution. A container image goes to a registry, and anyone
who can pull it receives every file inside. MIMIC samples belong in HF
[`MedOmni/family-samples`](https://huggingface.co/datasets/MedOmni/family-samples),
which Data & Task owns. They reach a container through the `/data` mount at run
time, and they are never built into an image.
