"""The audit matrix: five assets, four criteria, each cell a list of atomic checks and the auditors assigned to it
(`docs/reference/audit.md`). Each check's id is `<cell>.<n>`, numbered in order, as in v0.2's `audit-matrix.md`."""
from __future__ import annotations

PASS, WARN, FAIL, NONE = "pass", "warn", "fail", "unassessed"
ASSETS = {"data": "D", "families": "F", "encoders": "P", "tasks": "T", "runs": "R"}
DIMS = {"Completeness": "COMP", "Conformance": "CONF", "Isolation": "ISOL", "Clinical validity": "CLIN"}
AUDITOR = {"M": "machine", "L": "LLM (advisory)", "H": "human (sign-off)"}

_CHECKS = {
    "D-COMP": ["Required source files and manifests are present.",
               "Dataset version, provenance, license, and cohort counts are recorded.",
               "Required evidence streams and patient-level availability records are present."],
    "D-CONF": ["Files match the declared schema, data types, units, and hashes.",
               "Reported cohort and modality-availability statistics reproduce from the manifests.",
               "Source-specific filtering reproduces the declared data pool."],
    "D-ISOL": ["Direct identifiers and prohibited metadata are absent.",
               "Dataset, patient, and evaluation-split boundaries are preserved.",
               "Access is limited to the declared data roots."],
    "D-CLIN": ["The population and acquisition setting support the intended benchmark use.",
               "Missingness, coverage, and known biases are clinically characterized.",
               "The represented evidence retains its clinical meaning after preprocessing."],
    "F-COMP": ["Format, dimensionality, channel semantics, sampling rate, physical units, and accepted aliases are declared where applicable.",
               "Representative validation samples are available and fingerprinted.",
               "Reader and normalization requirements are documented."],
    "F-CONF": ["Pinned samples exactly satisfy the declared format and dimensionality.",
               "Channels, roles, sampling rates, units, and image encoding match the contract.",
               "Readers preserve the declared timing and measurement semantics."],
    "F-ISOL": ["Readers expose only declared payloads and metadata.",
               "File names, paths, aliases, and metadata do not reveal targets or gold labels.",
               "Runtime accommodations do not silently broaden the contract."],
    "F-CLIN": ["Channel, unit, and acquisition semantics match clinical practice.",
               "Clinically distinct acquisition protocols remain separate modality families.",
               "Normalization does not remove information required for clinical interpretation."],
    "P-COMP": ["Every registered learned or rule-based encoder has an encoder card, source revision, and runnable implementation.",
               "Runtime images, rule definitions, model weights where applicable, and reliability evidence are present.",
               "Service endpoints, routing metadata, health checks, and call logging are available."],
    "P-CONF": ["Encoder behavior matches its card, compatible modality families, and output contract.",
               "Inputs are routed only to compatible encoders.",
               "Service requests, responses, and logs follow the declared schemas.",
               "Reliability evidence satisfies the declared acceptance requirements."],
    "P-ISOL": ["Encoder containers can access only permitted read-only data roots.",
               "Path traversal and access to test, gold, or undeclared external data are rejected.",
               "Training provenance does not overlap prohibited evaluation data.",
               "Container and dependency isolation is preserved across encoders."],
    "P-CLIN": ["Intended use, outputs, limitations, and failure modes are clinically meaningful.",
               "Reliability evidence supports the claimed interpretation of encoder outputs.",
               "Output labels, scores, events, and text preserve their declared clinical semantics."],
    "T-COMP": ["The proposal, frozen specification, target derivation, prediction boundary, evidence policy, cohort rules, metric, and verifier are present.",
               "Every emitted instance contains all required evidence and task artifacts.",
               "Task and instance config hashes are recorded."],
    "T-CONF": ["Frozen specifications agree with proposal records and manifests.",
               "Rebuilding reproduces the task artifacts and config hashes.",
               "Patient-level instances satisfy the declared cohort, evidence, target, and output contracts.",
               "Verifiers implement the declared metric and failure policy."],
    "T-ISOL": ["Evidence observed after the prediction boundary is excluded.",
               "Target-defining, circular, or directly revealing evidence is excluded.",
               "Gold outputs and verifier internals are inaccessible to the agent.",
               "Patient evidence does not cross task-instance boundaries."],
    "T-CLIN": ["The question, target, population, and prediction time form a meaningful clinical task.",
               "Permitted evidence is clinically relevant and admissible at the decision point.",
               "Target derivation and exclusions support the intended clinical interpretation.",
               "Clinician review is bound to the audited task config hash."],
    "R-COMP": ["Run configuration, requested and served model identities, predictions, traces, verifier outputs, and ledger records are present.",
               "Runtime, token, cost, and failure records are retained.",
               "Every reported perception call appears in the service call log."],
    "R-CONF": ["The run uses the pinned task, perception service, agent, and model versions.",
               "Verifier replay reproduces the recorded score.",
               "Predictions satisfy the task output contract.",
               "Reported tool use agrees with the execution trace and service logs."],
    "R-ISOL": ["No agent or perception call accesses prohibited test, gold, or external patient data.",
               "Trial execution and external scoring remain separated.",
               "Parallel trials do not share patient evidence, state, or outputs."],
    "R-CLIN": ["Evidence-seeking behavior is clinically reasonable.",
               "Relevant available evidence is not systematically ignored without justification.",
               "Refusals, malformed outputs, timeouts, and unscorable outcomes remain explicit.",
               "Human review is bound to the run and task config hashes."],
}

_AUDITORS = {  # the reference page's table, per cell not already M only
    "D-CLIN": "LH", "F-ISOL": "ML", "F-CLIN": "LH", "P-ISOL": "ML", "P-CLIN": "LH", "T-ISOL": "ML", "T-CLIN": "LH",
    "R-ISOL": "ML", "R-CLIN": "LH",
}
DIM_OF = {v: k for k, v in DIMS.items()}
ASSET_OF = {v: k for k, v in ASSETS.items()}


def cells() -> dict:
    """{cell id: {asset, dim, auditors, checks: {check id: text}}}"""
    return {cid: {"asset": ASSET_OF[cid[0]], "dim": DIM_OF[cid[2:]], "auditors": list(_AUDITORS.get(cid, "M")),
                  "checks": {f"{cid}.{n}": text for n, text in enumerate(texts, 1)}}
            for cid, texts in _CHECKS.items()}
