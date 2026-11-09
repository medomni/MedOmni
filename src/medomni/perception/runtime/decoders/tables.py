"""Decoders for table and JSON families: measurements, CGM, numeric observations, wearables."""
import json
import math

from ..errors import Degraded


# Wide column -> canonical measurement name. A column absent from this map is
# not a measurement, is dropped, and is reported in notes. That is why the
# triage 'acuity' column never reaches an encoder.
_MEASUREMENT_COLUMNS = {
    "temperature": "body_temperature",
    "heartrate": "heart_rate",
    "resprate": "respiratory_rate",
    "o2sat": "oxygen_saturation",
    "sbp": "systolic_blood_pressure",
    "dbp": "diastolic_blood_pressure",
    "pain": "pain_score",
}

_METADATA_COLUMNS = {"subject_id", "stay_id", "charttime", "_t"}


def _read_measurements(path, root):
    """Read JSONL lab rows and reshape wide vital rows into measurements."""
    rows, unmapped, unparsed, nonfinite = [], set(), 0, 0
    unitless = False
    try:
        text = path.read_text()
    except UnicodeDecodeError as exc:
        # Bytes that are not text at all: a degraded input, not a caller error.
        raise Degraded(f"the file is not UTF-8 text: {exc}")
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except ValueError:
            unparsed += 1
            continue
        if not isinstance(raw, dict):
            unparsed += 1
            continue
        t = raw.get("_t") or raw.get("charttime") or raw.get("time") or raw.get("t")
        if "value" in raw and ("measurement" in raw or "name" in raw or "itemid" in raw):
            name = raw.get("measurement", raw.get("name"))
            if name is None and raw.get("itemid") is not None:
                name = "itemid:" + str(raw["itemid"])
            unit = raw.get("unit")
            itemid = raw.get("itemid")
            if (not isinstance(name, str) or not name.strip()
                    or (unit is not None and not isinstance(unit, str))
                    or (itemid is not None and (isinstance(itemid, bool)
                                               or not isinstance(itemid, (str, int))))):
                unparsed += 1
                continue
            try:
                if isinstance(raw["value"], bool):
                    raise ValueError("boolean is not a measurement")
                value = float(raw["value"])
            except (TypeError, ValueError):
                unparsed += 1
                continue
            if not math.isfinite(value):
                nonfinite += 1
                continue
            unit = (unit.strip() or None) if unit is not None else None
            unitless |= unit is None
            rows.append({"t": t, "name": name.strip(), "value": value, "unit": unit,
                         "itemid": str(itemid) if itemid is not None else None, "format": "long"})
            continue
        for col, value in raw.items():
            if col == "measurement" and raw[col] == "ed_vitalsign":
                continue
            if col in _METADATA_COLUMNS:
                continue
            name = _MEASUREMENT_COLUMNS.get(col)
            if name is None:
                unmapped.add(col)
                continue
            if value is None or str(value).strip() == "":
                continue          # missing, never zero
            try:
                num = float(value)
            except (TypeError, ValueError):
                unmapped.add(col)
                continue
            if not math.isfinite(num):
                nonfinite += 1
                continue
            rows.append({"t": t, "name": name, "value": num, "unit": None})
            unitless = True
    notes = []
    if unmapped:
        notes.append("columns not read, no measurement mapping: "
                     + ", ".join(sorted(unmapped)))
    if unparsed:
        notes.append(f"{unparsed} unreadable line(s) skipped")
    if nonfinite:
        notes.append(f"{nonfinite} non-finite measurement(s) skipped")
    if rows and unitless:
        notes.append("source declares no units; values are passed through unconverted")
    return {"kind": "measurements", "rows": rows, "notes": notes}


_CGM_MAX_JITTER_S = 30  # cgm-5min-mgdl.yaml omh_record.grid: observed device jitter < 30 s


def _read_cgm(path, root):
    """Open mHealth blood-glucose JSON -> five-minute grid, preserving gaps.

    Follows the family's pinned omh_record contract: a top-level object whose body.cgm
    is a list of records; time from date_time or else the time_interval start; device
    jitter snapped to the 300 s grid; "Low"/"High" readings lie outside the device range
    and are left out, counted, never imputed."""
    from datetime import datetime, timedelta, timezone
    notes = []
    try:
        records = json.loads(path.read_text())
        if isinstance(records, dict):
            body = records.get('body')
            if isinstance(body, dict) and isinstance(body.get('cgm'), list):
                records = [{'header': records.get('header'), 'body': item} for item in body['cgm']]
            else:
                records = [records]
        if not isinstance(records, list) or not records:
            raise ValueError("expected blood-glucose records")
        readings, censored = [], 0
        for record in records:
            schema = record['header']['schema_id']
            if schema['namespace'] != 'omh' or schema['name'] != 'blood-glucose':
                raise ValueError("expected the Open mHealth blood-glucose schema")
            body = record['body']
            glucose = body['blood_glucose']
            if glucose['unit'] != 'mg/dL':
                raise ValueError("the family requires mg/dL")
            value = glucose['value']
            if isinstance(value, str) and value.strip().lower() in ('low', 'high'):
                censored += 1
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("glucose must be a positive finite number")
            frame = body['effective_time_frame']
            when = frame.get('date_time') or frame['time_interval']['start_date_time']
            timestamp = datetime.fromisoformat(when.replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                raise ValueError("date_time must include a timezone")
            readings.append((timestamp.astimezone(timezone.utc).replace(tzinfo=None), float(value)))
        if not readings:
            raise ValueError("no numeric glucose readings")
        anchor = min(t for t, _ in readings)  # the device's own phase, not the wall clock
        observed, collisions, drift = {}, 0, 0.0
        for timestamp, value in sorted(readings):
            snapped = anchor + timedelta(seconds=round((timestamp - anchor).total_seconds() / 300) * 300)
            drift = max(drift, abs((timestamp - snapped).total_seconds()))
            if snapped in observed:
                collisions += 1
                continue
            observed[snapped] = value
        if drift > _CGM_MAX_JITTER_S:
            raise ValueError(f"timestamps lie {drift:.0f} s off the five-minute grid "
                             f"(jitter above {_CGM_MAX_JITTER_S} s is not a grid)")
        first, last = min(observed), max(observed)
        span = (last - first).total_seconds()
        if span > 90 * 86400:
            raise ValueError("CGM span exceeds 90 days")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise Degraded(f"cannot read CGM records: {exc}") from exc
    times = [first + timedelta(seconds=300*i) for i in range(int(span/300)+1)]
    missing = len(times) - len(observed)
    if drift:
        notes.append(f'timestamps snapped to the five-minute grid (max drift {drift:.0f} s)')
    if collisions:
        notes.append(f'{collisions} reading(s) landing on an occupied grid slot were dropped (first kept)')
    if censored:
        notes.append(f'{censored} reading(s) reported as Low/High (outside the device range) left out, not imputed')
    notes.append(f'{missing} missing five-minute slots; no values imputed')
    return {'kind': 'cgm', 'times': times,
            'glucose': [observed.get(t, math.nan) for t in times],
            'notes': notes}


def _read_numeric_observations(path, root):
    """Read numeric observations without filling absent clinical values."""
    rows, errors = [], 0
    try:
        raw = json.loads(path.read_text()) if path.suffix.lower() == '.json' else [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        raise Degraded(f'cannot read numeric observations: {exc}') from exc
    records = raw if isinstance(raw, list) else [raw]
    for record in records:
        if not isinstance(record, dict):
            errors += 1
            continue
        if 'observations' in record:
            nested = record['observations']
            if not isinstance(nested, list):
                errors += 1
                continue
            records.extend(nested)
            continue
        name, value = record.get('name'), record.get('value')
        unit = record.get('unit')
        if (not isinstance(name, str) or not name.strip()
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or (unit is not None and not isinstance(unit, str))):
            errors += 1
            continue
        rows.append(dict(name=name.strip(), value=float(value), unit=unit,
                         t=record.get('t') or record.get('time')))
    if errors:
        raise Degraded(f'{errors} numeric observation record(s) are invalid')
    if not rows:
        raise Degraded('no numeric observations found')
    return dict(kind='observations', rows=rows, notes=[])



def _read_wearable_omh(path, root, schema_name, field, container, unit):
    """Decode standard OMH records and AI-READI's nested arrays, without imputation."""
    from datetime import datetime, timezone
    try:
        records = json.loads(path.read_text())
        records = records if isinstance(records, list) else [records]
        observed = {}
        for record in records:
            schema = record['header']['schema_id']
            if schema['namespace'] != 'omh' or schema['name'] != schema_name:
                raise ValueError(f'expected OMH {schema_name}')
            body = record['body']
            entries = body.get(container)
            entries = entries if isinstance(entries, list) else [body]
            for entry in entries:
                measurement = entry[field]
                if measurement['unit'] != unit:
                    raise ValueError(f'{field} requires {unit}')
                value = measurement['value']
                if isinstance(value, bool) or not isinstance(value, (float, int)):
                    raise ValueError('measurement must be numeric')
                when = datetime.fromisoformat(entry['effective_time_frame']['date_time'].replace('Z', '+00:00'))
                if when.tzinfo is None:
                    raise ValueError('timestamp requires timezone')
                when = when.astimezone(timezone.utc)
                if when in observed:
                    raise ValueError('duplicate measurement timestamp')
                observed[when] = float(value)
        if not observed:
            raise ValueError('no measurements')
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
        raise Degraded(f'cannot read wearable OMH: {exc}') from exc
    times = sorted(observed)
    return dict(kind='wearable', times=times, values=[observed[t] for t in times],
                units=unit, notes=['Timestamps sorted; gaps preserved without interpolation.'])


def _read_wearable_hr(path, root):
    return _read_wearable_omh(path, root, 'heart-rate', 'heart_rate', 'heart_rate', 'beats/min')


def _read_wearable_resp(path, root):
    return _read_wearable_omh(path, root, 'respiratory-rate', 'respiratory_rate', 'breathing', 'breaths/min')


def _read_wearable_spo2(path, root):
    return _read_wearable_omh(path, root, 'oxygen-saturation', 'oxygen_saturation', 'breathing', '%')
