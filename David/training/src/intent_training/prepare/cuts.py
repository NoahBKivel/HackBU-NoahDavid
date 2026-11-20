"""Select visible positive cuts and match clean negative event positions."""

from collections import Counter, defaultdict

from monitor_format import is_cut_point


def _positive(question, value):
    if question == "G1":
        return value is False
    if question == "G2":
        return value in ("broken", "not done")
    return value is True


def positive_offense(row):
    """Return the first explicitly localized visible offence, without using outcomes."""
    side, meta = row.get("side", {}), row.get("meta", {})
    seqs = [label["event_seq"] for label in side.get("source_labels", [])
            if label.get("basis") in {"visible", "V"}
            and isinstance(label.get("event_seq"), int)
            and _positive(label.get("question"), label.get("value"))]
    intended = side.get("construction", {}).get("intended", {})
    if any(_positive(question, value) for question, value in intended.items()):
        if isinstance(meta.get("cut_seq"), int):
            seqs.append(meta["cut_seq"])
    return min(seqs) if seqs else None


def _event_type(event):
    if event["type"] == "turn_completed":
        return "message"
    tool = event.get("action", {}).get("tool")
    if tool in {"Edit", "Write"}:
        return "edit_write"
    if tool in {"Bash", "PowerShell"}:
        return "shell"
    if tool in {"TodoWrite", "ExitPlanMode"}:
        return "plan"
    return "other"


def _cut(row, position, kind, harness):
    event = row["events"][position]
    return {"cut_seq": event["seq"], "cut_kind": kind,
            "match_harness": harness, "event_type": _event_type(event),
            "index_bin": position // 10}


def _clean(row):
    side, meta = row.get("side", {}), row.get("meta", {})
    if side.get("source_category") == "negative" or meta.get("cut_kind") == "negative":
        return True
    labels = [label for label in side.get("source_labels", [])
              if label.get("basis") in {"visible", "V"}]
    def declared_negative(label):
        question, value = label.get("question"), label.get("value")
        if question == "G1":
            return value is True
        if question == "G2":
            return value == "done"
        return value is False
    return bool(labels) and all(declared_negative(label) for label in labels)


def plan_cuts(rows):
    """Return aligned cut lists; unmatched negatives remain absent rather than fabricated."""
    result = [[] for _ in rows]
    positives = defaultdict(list)
    vocabularies = defaultdict(set)
    candidates = []
    for index, row in enumerate(rows):
        harness = row.get("meta", {}).get("harness") or "unspecified"
        events = row.get("events", [])
        vocabularies[harness].update(event.get("action", {}).get("tool") for event in events
                                     if event.get("action", {}).get("tool"))
        offense = positive_offense(row)
        classified = [position for position, event in enumerate(events) if is_cut_point(event)]
        if not classified:
            continue
        if offense is not None:
            position = next((p for p in classified if events[p]["seq"] >= offense), None)
            if position is not None:
                cut = _cut(row, position, "positive", harness)
                result[index].append(cut)
                positives[harness].append(cut)
            for p in classified:
                if events[p]["seq"] < offense:
                    candidates.append((index, p, harness, "negative_prefix"))
        elif _clean(row):
            candidates.extend((index, p, harness, "negative") for p in classified)
        else:
            declared = row.get("meta", {}).get("cut_seq")
            position = next((p for p in classified if events[p]["seq"] == declared), None)
            if declared is None:
                position = classified[-1]
            if position is not None:
                result[index].append(_cut(row, position, "candidate", harness))

    # Connected nearest-neighbour groups share one joint distribution.
    parents = {harness: harness for harness in vocabularies}

    def find(harness):
        while parents[harness] != harness:
            parents[harness] = parents[parents[harness]]
            harness = parents[harness]
        return harness

    for harness in sorted(vocabularies):
        if len(positives[harness]) >= 20:
            continue
        alternatives = [other for other in vocabularies
                        if other != harness and positives[other]]
        if not alternatives:
            continue
        def distance(other):
            left, right = vocabularies[harness], vocabularies[other]
            union = left | right
            return (1 - len(left & right) / len(union) if union else 0, other)
        nearest = min(alternatives, key=distance)
        left, right = find(harness), find(nearest)
        if left != right:
            parents[left] = right
    components = defaultdict(list)
    for harness in vocabularies:
        components[find(harness)].append(harness)
    pooled = {}
    for members in components.values():
        anchors = [harness for harness in members if len(positives[harness]) >= 20]
        canonical = min(anchors or members)
        pooled.update({harness: canonical for harness in members})
    distributions = defaultdict(Counter)
    for harness, cuts in positives.items():
        pool = pooled.get(harness, harness)
        for cut in cuts:
            distributions[pool][cut["event_type"], cut["index_bin"]] += 1
    available = defaultdict(list)
    for index, position, harness, kind in candidates:
        cut = _cut(rows[index], position, kind, pooled.get(harness, harness))
        available[cut["match_harness"], cut["event_type"], cut["index_bin"]].append((index, cut))
    used = set()
    for pool, distribution in sorted(distributions.items()):
        eligible = {index for event_type, index_bin in distribution
                    for index, _ in available[pool, event_type, index_bin]}
        total = sum(distribution.values())
        quotas = {bucket: len(eligible) * count // total
                  for bucket, count in distribution.items()}
        remainder = len(eligible) - sum(quotas.values())
        order = sorted(distribution, key=lambda bucket: (
            -(len(eligible) * distribution[bucket] % total), bucket))
        for bucket in order[:remainder]:
            quotas[bucket] += 1
        for (event_type, index_bin), desired in sorted(quotas.items()):
            if not desired:
                continue
            for index, cut in available[pool, event_type, index_bin]:
                if index in used:
                    continue
                used.add(index)
                result[index].append(cut)
                desired -= 1
                if desired == 0:
                    break
    return result
