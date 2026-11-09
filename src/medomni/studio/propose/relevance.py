"""`medomni studio relevance <template>`: the one human-labelled relevance table scoring reads for a template.

Each stream a proposer listed is mapped to a family id: declared (the dataset can stage it, the recall denominator),
declared_unstaged (named but not stageable), banned (the scoring source itself). Class labels copied into the streams
column are dropped and counted. No proposal on file: the template's own `input` block is the declaration.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from ..survey.dataset import CMI, CRT, declared_families
from ..tools import Propose, Result, ToolError
from .intake import propose_id, read_rows, chips

MIMIC_WAVES = ["abp-waveform-125hz-mmhg", "ecg-monitor-3to5lead-250hz-continuous", "ppg-waveform-uncal",
               "pressure-nonarterial-125hz-mmhg", "resp-impedance-62hz-ohm"]
LAB = re.compile(r"\((Blood|Urine|Other Body Fluid|Ascites|Pleural|Joint Fluid|Cerebrospinal Fluid|Stool|"
                 r"Fluid|Bone Marrow|Blood Gas)[^)]*\)")

# stream label -> families; "UNSTAGED:<what>": named, but no stager writes it; "BANNED:<family>"; "LABEL": a class label
STREAMS = {
    "bdsp": {
        "Sleep EEG": ["eeg-sleep-6ch-200hz-uv"], "Electro-oculogram": ["eog-2ch-200hz-uv"],
        "Chin EMG": ["emg-chin-200hz-uv"], "Limb EMG": ["emg-limb-200hz-uv"],
        "Single-lead ECG": ["ecg-1lead-200hz-uv"], "Pulse oximeter plethysmogram": ["ppg-waveform-uncal"],
        "Oxygen saturation": ["spo2-series-10hz-pct"], "Pulse rate": ["pulse-rate-10hz-bpm"],
        "Respiratory rate": ["resp-flow"],  # derived from airflow: BDSP has no respiratory-rate family
        "Respiratory effort belts": ["resp-effort-rip-2ch-50hz"], "Airflow": ["resp-flow"],
        "Snore": ["snore-acoustic"], "Body position": ["body-position-code-10hz"],
        "Capnography": ["capnography-mmhg"], "EHR record": [CRT], "PSG session metadata": [CRT],
        "Actigraphy": ["UNSTAGED:actigraphy"], "CPAP": ["UNSTAGED:cpap-telemetry"],
        "12-lead ECG acquisitions": ["UNSTAGED:muse-12lead-index-only"],
        "Technologist sleep staging": ["BANNED:psg-annotations"],  # the scoring source of every PSG target
        "Female": ["LABEL"], "Male": ["LABEL"], "Age >= 65": ["LABEL"], "Race:": ["LABEL"], "Deceased": ["LABEL"],
    },
    "aireadi": {
        "Colour fundus photograph": ["fundus-photography-2d"], "OCT angiography — en-face": ["octa-enface-slab-mono8-2d"],
        "OCT angiography — flow cube": ["octa-flowcube-mono8-3d"], "Structural OCT volume": ["oct-volume-raster-mono8-3d"],
        "OCT retinal surface segmentation": ["retinal-heightmap-surfaces-f32"],
        "Continuous glucose monitor": ["cgm-5min-mgdl"], "12-lead resting ECG": ["ecg-12lead-500hz-mv"],
        "Wrist heart rate": ["wearable-hr-1min-bpm"], "Wrist SpO": ["wearable-spo2-1min-pct"],
        "Wrist respiratory rate": ["wearable-resprate-1min-brpm"],
        "Step count": ["numeric-observation"], "Energy expenditure": ["numeric-observation"],
        "Wearable sleep staging": ["numeric-observation"], "Wearable stress score": ["numeric-observation"],
        "Home environmental sensor": ["UNSTAGED:environmental-sensor"],
        "Clinical record": [CRT, CMI],
        **{k: [CMI] for k in ("HbA1c", "Serum glucose", "Total cholesterol", "LDL cholesterol", "HDL cholesterol",
                              "Triglycerides", "Creatinine", "hs-CRP", "Insulin", "C-peptide", "Urine albumin",
                              "Urine creatinine", "Urea nitrogen", "BMI", "Weight", "Waist circumference",
                              "Waist-to-hip ratio", "Systolic blood pressure", "Diastolic blood pressure",
                              "Resting heart rate", "Photopic visual acuity", "Autorefraction",
                              "Photopic contrast sensitivity")},
        **{k: [CRT] for k in ("Alcohol use", "Cannabis use", "CES-D-10", "Diabetes lifestyle survey", "Diet score",
                              "Discrimination in health care", "Driving habits", "Education level", "Family history",
                              "Food insecurity", "Health insurance", "Medication use survey", "Neighbourhood environment",
                              "PAID-5", "Racial / ethnic discrimination", "Smoking history", "Vaping",
                              "Vision-related difficulty", "Years of education", "Healthy (no diabetes)", "Pre-diabetes",
                              "Type 2 diabetes", "Type II Diabetes", "Diabetic retinopathy", "Elevated A1C",
                              "High blood cholesterol", "High blood pressure")},
    },
    "mimic-iv": {
        "12-lead diagnostic ECG": ["ecg-12lead-500hz-mv"], "Chest X-ray images": ["cxr-radiograph-2d"],
        "CheXpert labels": ["cxr-radiograph-2d"],
        **{k: ["cxr-radiograph-2d"] for k in ("Atelectasis", "Cardiomegaly", "Consolidation", "Edema",
                                              "Enlarged Cardiomediastinum", "Lung Lesion", "Lung Opacity", "No Finding",
                                              "Pleural Effusion", "Pneumonia", "Support Devices")},
        "ICU bedside monitor waveforms": MIMIC_WAVES, "ICU monitor numerics": ["numeric-observation"],
        "Laboratory results": [CMI], "ED vital signs": [CMI], "Outpatient measurements": [CMI],
        "Hospital admissions & patient demographics": [CRT], "Hospital ICD diagnosis history": [CRT],
        "ED stays": [CRT], "ED triage": [CRT], "Sex:": [CRT], "Race/ethnicity:": [CRT], "Age >= 65": [CRT],
        "Microbiology cultures": ["UNSTAGED:microbiology"], "Prescriptions": ["UNSTAGED:prescriptions"],
        "Medication administration": ["UNSTAGED:emar"], "Hospital ICD procedures": ["UNSTAGED:procedures"],
        "ED medication reconciliation": ["UNSTAGED:ed-medrecon"], "ICU bedside charted observations": ["UNSTAGED:icu-chartevents"],
        "ICU fluid inputs": ["UNSTAGED:icu-inputs-outputs"], "ICU stays": ["UNSTAGED:icustays"],
        "Ward transfers": ["UNSTAGED:transfers"],
        "Radiology reports": ["clinical-free-text"], "Discharge summaries": ["clinical-free-text"],
    },
}


def classify(dataset: str, label: str) -> list[str]:
    for key, fams in STREAMS.get(dataset, {}).items():
        if label.startswith(key):
            return fams
    if dataset == "mimic-iv":
        return [CMI] if LAB.search(label) else [CRT]  # the remaining MIMIC labels are diagnosis categories
    return ["UNMAPPED"]


def table(dataset: str, streams: list[str], expected: set[str]) -> dict:
    from medomni.core import families

    known = set(families.load_registry())
    declared, unstaged, banned, unmapped, labels = set(), set(), set(), set(), 0
    for lab in streams:
        for f in classify(dataset, lab):
            if f == "LABEL":
                labels += 1
            elif f == "UNMAPPED":
                unmapped.add(lab)
            elif f.startswith("BANNED:"):
                banned.add(f[7:])
            elif f.startswith("UNSTAGED:"):
                unstaged.add(f[9:])
            elif f not in known:  # a retired family is no family: keep the stream it named
                unstaged.add(f.split("-")[0])
            elif f in expected:
                declared.add(f)
            else:
                unstaged.add(f)
    return {"declared": sorted(declared), "declared_unstaged": sorted(unstaged), "banned": sorted(banned),
            "class_labels_dropped": labels, "unmapped": sorted(unmapped)}


def _matched(rows: list[dict], template: str, dataset: str) -> list[dict]:
    """The rows whose title gives this template id (v0.2 matched on the title's prefix, now on the id it produced)."""
    taken: set[str] = set()
    return [r for r in rows if r.get("dataset") == dataset and propose_id(r.get("title", ""), dataset, taken) == template]


class Relevance(Propose):
    name = "relevance"
    summary = "write the relevance table that scoring reads for a template"
    target = "template"

    def options(self, p) -> None:
        p.add_argument("--proposals", type=Path, help="the proposals .csv (default: use the template's input block)")

    def make(self, target, a, ctx) -> Result:
        from medomni.core.contracts import TaskTemplate, load
        from medomni.core.loading import find_package

        template = target.split("@")[0].split(":")[0]
        dataset = template.split("_", 1)[0]
        try:
            package = find_package(dataset)
        except FileNotFoundError as e:
            raise ToolError(str(e)) from None
        tp = package / "tasks" / template / "template.yaml"
        if not tp.is_file():
            raise ToolError(f"no template {template} in {package}")
        tpl = load(tp, TaskTemplate)
        expected = declared_families(package)
        rows = _matched(read_rows(a.proposals), template, dataset) if a.proposals else []
        if rows:
            entry = table(dataset, [lab for r in rows for lab in chips(r.get("streams", ""))], expected)
            entry["source"] = " + ".join(sorted({r["title"][:70] for r in rows}))
        else:  # no proposal on file: the template's input block is the declaration
            inp = tpl.input
            declared = {f for f in inp.get("families", ()) if f in expected}
            if inp.get("tables") or inp.get("demographics"):
                declared |= {CRT}
            if inp.get("labs"):
                declared |= {CMI}
            entry = {"declared": sorted(declared), "declared_unstaged": [], "banned": [], "class_labels_dropped": 0,
                     "unmapped": [], "source": "the template's input block (no proposal on file)"}
        doc = {template: entry}
        text = (f"# relevance table for {template}: the families its proposer declared relevant, as family ids.\n"
                "# Draft until a reviewer signs it. The recall denominator is declared ∩ staged.\n"
                + yaml.safe_dump(doc, sort_keys=True, allow_unicode=True, width=200))
        return Result(f"{template}: {len(entry['declared'])} declared, {len(entry['declared_unstaged'])} unstaged, "
                      f"{len(entry['banned'])} banned", {f"{template}.yaml": text})
