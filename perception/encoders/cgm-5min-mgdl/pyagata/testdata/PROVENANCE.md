# Fixture

`input.json` is an authored Open mHealth example, with no patient data.
Values are 60, 70, missing, 180, and 200 mg/dL on a five-minute grid.
The mean is 127.5 mg/dL, inclusive range coverage is 50%, and missingness is 20%.
The frozen output checks implementation consistency, not clinical accuracy.

Schema: https://github.com/openmhealth/schemas/blob/master/schema/omh/blood-glucose-3.0.json
No CGM sample is currently staged in MedOmni/family-samples.
