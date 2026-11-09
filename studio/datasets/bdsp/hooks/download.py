"""Where BDSP's files are on its server, and where this package reads them (`medomni studio download-list bdsp`).

BDSP reorganised its server on 2026-10-28; the nights there are the same ones. Each pair is (server key, path in your copy).
A key ending in `/` is a folder, copied whole.
"""
from __future__ import annotations

SITE = "PSG/bids/I0006"
PARQUET = "EHR/I0006-EHR/data_Structured/Parquet/Parquet"
METADATA = "I0006_psg_metadata_2025-07-09.csv"


def index_files() -> list[tuple[str, str]]:
    """The tables that say who the patients are: needed first, whatever part of the dataset you download."""
    return [(f"PSG/psg-metadata/{METADATA}", f"_index/psg-metadata/{METADATA}"),
            (f"{PARQUET}/bdsp_i0006_demographics/", "_index/ehr_labels/demographics/"),
            (f"{PARQUET}/bdsp_i0006_diagnosis/", "_index/ehr_labels/diagnosis/")]


def night_files(params: dict, m: dict) -> list[tuple[str, str]]:
    """One patient's night: the recording, its sleep stages and its scored events."""
    folder, ses = m["BIDSFolder"], f"ses-{m['SessionID']}"
    stem, local = f"{folder}_{ses}", params["night"].format(folder=folder, session=m["SessionID"])
    psg = f"{SITE}/primary/{folder}/{ses}/psg/{stem}_task-psg"
    return [(f"{SITE}/sourcedata/{folder}/{ses}/{stem}.h5", local),
            (f"{psg}_sleepstage.csv", local.replace(".h5", "_scores.csv")),
            (f"{psg}_eventannotations.csv", local.replace(".h5", "_events.csv"))]
