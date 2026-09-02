#!/usr/bin/env python3
"""Fetch the PTB-XL records this encoder is tested against.

Three real twelve-lead ECGs, chosen because each carries a finding the card
declares: a normal ECG, atrial fibrillation, and a chronic inferior infarct.
PROVENANCE.md records where each one comes from and what its license permits.

    python fetch_input.py

Every file is checked against the sha256 pinned below, which is the sha256
PhysioNet publishes in the dataset's own SHA256SUMS.txt. A download that does
not match fails, instead of being frozen into expected.json.

TWO FIELDS ARE REWRITTEN, AND NOTHING ELSE.

A WFDB record is two files: a text header, and the signal file that the header
names. The test harness treats every `input*` file in this directory as one
sample, and a signal file is not a sample — it is half of one. So the header
carries the `input-` prefix and the signal file does not.

The signal file is therefore byte-identical to the published .dat and keeps the
published sha256. The header is rewritten in exactly two places: the record name
on line 1, and the file name that begins each signal line. Gains, baselines and
per-signal checksums are untouched, because the samples are untouched.

Standard library only, so the fixture rebuilds on any machine. The output is
committed, as torchxrayvision's make_input.py commits its own.
"""
import hashlib
import urllib.request
from pathlib import Path

BASE = "https://physionet.org/files/ptb-xl/1.0.3"
HERE = Path(__file__).resolve().parent

# ecg_id -> PTB-XL stem, and the published sha256 of the header and the signal
# file. Pinned here rather than read from SHA256SUMS.txt at run time: a pin that
# the source can change is not a pin.
RECORDS = {
    "00057": ("records500/00000/00057_hr",
              "ffc96d075363ceeaa83aeaeb8239f0cda6d9984e1afea67f5f89005eccf0d76e",
              "1339a5f8000982272f0e49893506baeafb357994a171b665198d67c84b873870"),
    "01737": ("records500/01000/01737_hr",
              "3dd77cfe24b6d3fe1143f0e482b72eeadde6d378ef008c6b0acbba73294c1538",
              "5a4c21d08db31b5b6c72fd0242583994e53b50088e4ab2ec149717c1f241e711"),
    "08215": ("records500/08000/08215_hr",
              "e6c5763e429eeab3262ac0d3b0df488b0c2c07ff6a8c223ae9e16066e1335178",
              "58639475a1b1c36a2c5ee3cb4ce68cc872e7e85521324f9b691b7c215d4d84f4"),
}


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def rewrite_header(text, record_name, signal_name):
    """Point a WFDB header at a renamed signal file.

    Line 1 is `<record> <nsig> <fs> <nsamp>`; every signal line begins with the
    name of the file its samples live in. Nothing else is touched.
    """
    lines = text.splitlines()
    head = lines[0].split()
    head[0] = record_name
    out = [" ".join(head)]
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            out.append(line)
            continue
        fields = line.split(maxsplit=1)
        out.append(f"{signal_name} {fields[1]}" if len(fields) > 1 else signal_name)
    return "\n".join(out) + "\n"


def main():
    for ecg_id, (stem, hea_sha, dat_sha) in RECORDS.items():
        record_name = f"input-ptbxl-{ecg_id}"
        signal_name = f"ptbxl-{ecg_id}.dat"
        for suffix, expected, target in ((".dat", dat_sha, signal_name),
                                         (".hea", hea_sha, f"{record_name}.hea")):
            source = f"{stem}{suffix}"
            blob = fetch(f"{BASE}/{source}")
            digest = hashlib.sha256(blob).hexdigest()
            if digest != expected:
                raise SystemExit(
                    f"{source}: sha256 {digest}\n  does not match the pin {expected}")
            if suffix == ".hea":
                blob = rewrite_header(blob.decode(), record_name, signal_name).encode()
            (HERE / target).write_bytes(blob)
            print(f"wrote {target:24s} from {source}  (sha256 verified)")


if __name__ == "__main__":
    main()
