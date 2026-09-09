# Fixture

`input.json` is an authored Open mHealth example, with no patient data.
Values are 60, 70, missing, 180, and 200 mg/dL on a five-minute grid.
The mean is 127.5 mg/dL, inclusive range coverage is 50%, and missingness is 20%.
The frozen output checks implementation consistency, not clinical accuracy.

Schema: https://github.com/openmhealth/schemas/blob/master/schema/omh/blood-glucose-3.0.json
No CGM sample is currently staged in MedOmni/family-samples.

## Published CGM example

`input-dexcom.json` contains 289 observed glucose values from participant 001's first 24 hours in BIG IDEAs Lab Glycemic Variability and Wearable Device Data 1.1.3.
Source: https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/
File: `001/Dexcom_001.csv`; SHA-256 `6333b21185f23834ab929e5d8bf9045bbed6268cdfd5030adab3c7d5ef689ef5`.
Citation: Cho et al. (2026), dataset 1.1.3, DOI 10.13026/aw6y-fc44; Bent et al. (2021), DOI 10.1038/s41746-021-00465-w.
Contains information from this dataset, made available under the ODC Attribution License 1.0:
https://physionet.org/content/big-ideas-glycemic-wearable/view-license/1.1.3/
This derived fixture retains that license.

Only EGV events are used. Glucose values remain unchanged, in mg/dL.
`dexcom-source.csv` preserves the selected source timestamps and values for audit.
Source timestamps have no timezone. Elapsed time from the first observation (2020-02-13T17:23:32) is anchored at 2000-01-01T00:00:00+00:00 solely for the API.
The anchor is not the acquisition date or a claim about its timezone.
Elapsed times are rounded to the nearest 300 seconds; the largest adjustment is 2 seconds.
No observations collide after rounding. Missing slots remain missing; values are never interpolated.
