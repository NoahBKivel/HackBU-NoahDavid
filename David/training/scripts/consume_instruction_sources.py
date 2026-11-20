"""Materialize completed instruction-source responses without provider calls."""

import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent)]

from intent_training.generation.request_io import fingerprint
from intent_training.prepare.sample import available_ram_gib
from monitor_format import validate_events


def atomic_text(path, text):
    """Replace a complete artifact without exposing a partial write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".consumer.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def generation_id(slug, side, meta):
    """Resolve the original central request identity from source provenance."""
    if slug == "userbench":
        return meta["source_record_id"]
    if slug == "ambig_swe":
        return meta["trajectory_id"]
    if slug == "in3":
        return side["generation_id"]
    if slug == "if_multi":
        return f"if_multi-{meta['row_idx']:05d}"
    return side["generation"]["request_id"]


def checker_inputs(converter, requests, responses):
    """Export real completed answers for the existing isolated official checker."""
    output = []
    for index, row in converter.source_rows(ROOT / "data/downloads/if_multi"):
        if not 200 <= index < 400:
            continue
        identifier = converter.request_id(index)
        path = responses / (identifier + '.json')
        if not path.exists():
            continue
        try:
            context, envelope = converter.generated_context(index, row, responses)
        except (ValueError, TypeError, KeyError, IndexError):
            continue
        if (envelope.get('status') != 'completed' or envelope.get('stop_reason') in {'refusal', 'max_tokens'}
                or envelope.get('request_hash') != fingerprint(requests[identifier])):
            continue
        _, _, identifiers, kwargs = converter.parse_row(row)
        output.append({'id': identifier, 'instruction_ids': identifiers,
                       'kwargs': kwargs, 'response': context['response']})
    path = ROOT / 'data/generation/checker_requests/if_multi.jsonl'
    atomic_text(path, ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in output))
    return {'isolated_checker_inputs': len(output), 'isolated_checker_input_path': str(path.relative_to(ROOT)),
            'isolated_checker_input_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def consume(slug, patterns):
    """Validate actual cached evidence and atomically publish one source."""
    request_path = ROOT / "data/generation/requests" / (slug + ".jsonl")
    requests = {row["id"]: row for row in
                (json.loads(line) for line in request_path.open(encoding="utf-8") if line.strip())}
    responses = ROOT / "data/generation/responses"
    available = sum((responses / (key + ".json")).exists() for key in requests)
    if not available:
        return {"source": slug, "cached_envelopes": 0, "changed": False}
    converter = importlib.import_module("intent_training.sources." + slug)
    records, consumed, rejected = [], set(), []
    options = {"errors": rejected} if slug in {"if_multi", "in3"} else {}
    for events, side, meta in converter.convert(ROOT / "data/downloads" / slug, **options):
        validate_events(events)
        if meta.get("source") != slug or not meta.get("source_record_id") or not meta.get("licence"):
            raise ValueError("A converted source record lacks its identity or licence.")
        identifier = generation_id(slug, side, meta)
        if identifier in requests:
            path = responses / (identifier + ".json")
            envelope = json.loads(path.read_text(encoding="utf-8"))
            expected = fingerprint(requests[identifier])
            if (envelope.get("id") != identifier or envelope.get("request_hash") != expected
                    or envelope.get("status") != "completed"
                    or envelope.get("stop_reason") in {"refusal", "max_tokens"}
                    or not envelope.get("model") or not envelope.get("text", "").strip()):
                raise ValueError("A response is not a complete matching central generation artifact.")
            side["generation_provenance"] = {
                "request_id": identifier, "request_hash": expected,
                "response_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "model": envelope["model"], "usage": envelope["usage"],
                "cost_usd": envelope["cost_usd"], "stop_reason": envelope["stop_reason"]}
            consumed.add(identifier)
        elif not (slug == "if_multi" and meta["row_idx"] < 200 and meta["variant"] == "verbatim"):
            raise ValueError("A generated source record has no corresponding original request.")
        record = {"events": events, "side": side, "meta": meta}
        text = json.dumps(record, ensure_ascii=False)
        if any(re.search(pattern, text) for pattern in patterns):
            raise ValueError("A converted source record failed the credential scan.")
        records.append(record)
    rebalance_dropped = 0
    if slug == 'in3':
        groups = {True: [], False: []}
        for record in records:
            pair = record['meta']['pair_id']
            bucket = groups[record['side']['vague']]
            if pair not in bucket:
                bucket.append(pair)
        per_class = min(map(len, groups.values()))
        keep = {pair for bucket in groups.values() for pair in bucket[:per_class]}
        balanced = [record for record in records if record['meta']['pair_id'] in keep]
        rebalance_dropped = len(records) - len(balanced)
        records = balanced
        consumed = {record['side']['generation_provenance']['request_id'] for record in records}
    output = ROOT / "data/converted" / (slug + ".jsonl")
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    changed = not output.exists() or hashlib.sha256(output.read_bytes()).hexdigest() != digest
    if changed:
        atomic_text(output, text)
    report_path = ROOT / "results/sources" / (slug + ".json")
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    labels = {}
    for row in records:
        for label in row["side"].get("source_labels", []):
            key = f"{label['question']}:{label['value']}:{label['basis']}"
            labels[key] = labels.get(key, 0) + 1
    terminal = {'refused': set(), 'incomplete': set()}
    for status in terminal:
        for path in (ROOT / 'results/generation').glob('*.' + status + '.json'):
            envelope = json.loads(path.read_text(encoding='utf-8'))
            identifier = envelope.get('id')
            if identifier in requests and not (responses / (identifier + '.json')).exists():
                terminal[status].add(identifier)
    terminal['incomplete'] -= terminal['refused']
    reservation_path = ROOT / 'results/generation/reservations.json'
    reservations = json.loads(reservation_path.read_text(encoding='utf-8')) if reservation_path.exists() else {}
    open_requests = set()
    for job, reservation in reservations.items():
        identifier = job.split('.attempt', 1)[0]
        if (identifier in requests and 'charged_usd' not in reservation
                and not (responses / (identifier + '.json')).exists()):
            open_requests.add(identifier)
    terminal['incomplete'] -= open_requests
    result = {"source": slug, "cached_envelopes": available, "converted_records": len(records),
              "validated_records": len(records), "converted_count": len(records),
              "records_written": len(records), "generation_responses_consumed": len(consumed),
              "generation_responses": available,
              "rebalance_dropped_records": rebalance_dropped,
              "terminal_refusals": len(terminal['refused']),
              "terminal_incomplete": len(terminal['incomplete']),
              "open_generation_reservations": len(open_requests),
              "pending_generation": len(requests) - available - len(set.union(*terminal.values())),
              "visible_and_hint_labels": labels,
              "positive_count": sum(row["meta"].get("cut_kind") == "positive" for row in records),
              "negative_count": sum(row["meta"].get("cut_kind") == "negative" for row in records),
              "request_sha256": hashlib.sha256(request_path.read_bytes()).hexdigest(),
              "output_sha256": digest, "credential_findings": 0, "changed": changed,
              "rejected_generated_contexts": rejected}
    if slug == 'if_multi':
        result.update(checker_inputs(converter, requests, responses))
        answers = sum(row['meta']['objective'] != ['RF'] for row in records)
        verified = sum(any(label['question'] == 'M2' and label['basis'] == 'visible'
                           for label in row['side'].get('source_labels', [])) for row in records)
        result.update(records_by_objective={'RF': len(records) - answers, 'M2_D2_G2': answers},
                      output_rf_positive_units=labels.get('RF:True:visible', 0),
                      output_rf_negative_units=labels.get('RF:False:visible', 0),
                      answer_records=answers, verified_generated_responses=verified,
                      checks_pending_records=sum(row['side'].get('checks_pending', False) for row in records))
        result['isolated_checks_available'] = sum(1 for _ in (ROOT / 'data/downloads/if_multi/checks').glob('*.json'))
    if 'filters' in report and isinstance(report['filters'], dict):
        report['filters']['awaiting_generation'] = result['pending_generation']
    if slug in {"ambig_swe", "swe_annotations"}:
        exclusion = ROOT / "data/exclusions" / (slug + ".jsonl")
        known = {}
        if exclusion.exists():
            for line in exclusion.open(encoding="utf-8"):
                row = json.loads(line)
                known[row["instance_id"]] = row
        for row in records:
            identifier = row["meta"]["task_id"]
            known.setdefault(identifier, {"source": slug, "instance_id": identifier,
                                          "reason": "Issue used for training generation."})
        atomic_text(exclusion, "".join(json.dumps(row) + "\n" for row in known.values()))
        result["excluded_instance_ids"] = len(known)
    report.update(result)
    atomic_text(report_path, json.dumps(report, indent=2) + "\n")
    return result


def main():
    """Consume bounded cached sources under the owner's assigned local slot."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--follow-seconds', type=float, default=0)
    parser.add_argument("sources", nargs="+", choices=["userbench", "ambig_swe", "if_multi", "in3", "infobench", "swe_annotations"])
    args = parser.parse_args()
    memory = available_ram_gib()
    if memory <= 3.5:
        print(json.dumps({"status": "RAM_GATE_CLOSED", "available_gib": memory}), flush=True)
        return 75
    scanner_spec = importlib.util.spec_from_file_location("source_scan", ROOT / "scripts/scan_secrets.py")
    scanner = importlib.util.module_from_spec(scanner_spec)
    scanner_spec.loader.exec_module(scanner)
    results, previous = [], {}
    for slug in args.sources:
        path = ROOT / 'results/sources' / (slug + '.json')
        report = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        previous[slug] = (report.get('cached_envelopes', -1), report.get('isolated_checks_available', 0))
    deadline = time.monotonic() + args.follow_seconds
    while True:
        names = {path.stem for path in (ROOT / 'data/generation/responses').glob('*.json')}
        for slug in args.sources:
            request_path = ROOT / 'data/generation/requests' / (slug + '.jsonl')
            identifiers = {json.loads(line)['id'] for line in request_path.open(encoding='utf-8') if line.strip()}
            checks = sum(1 for _ in (ROOT / 'data/downloads/if_multi/checks').glob('*.json')) if slug == 'if_multi' else 0
            signature = (len(names & identifiers), checks)
            if args.follow_seconds and signature == previous[slug]:
                continue
            memory = available_ram_gib()
            if memory <= 3.5:
                print(json.dumps({'source': slug, 'status': 'RAM_GATE_CLOSED', 'available_gib': memory}), flush=True)
                continue
            try:
                result = consume(slug, scanner.PATTERNS)
            except Exception as error:
                result = {"source": slug, "error_type": type(error).__name__, "error": str(error)}
            previous[slug] = signature
            results.append(result)
            concise = {key: value for key, value in result.items() if key != 'rejected_generated_contexts'}
            concise['rejected_generated_context_count'] = len(result.get('rejected_generated_contexts', []))
            print(json.dumps(concise), flush=True)
        if not args.follow_seconds or time.monotonic() >= deadline:
            break
        time.sleep(min(20, max(0, deadline - time.monotonic())))
    atomic_text(ROOT / "results/sources/instruction-consumption.json", json.dumps(
        {"available_gib_at_start": memory, "sources": results}, indent=2) + "\n")
    return int(any("error" in result for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
