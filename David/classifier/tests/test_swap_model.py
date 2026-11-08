import json
import math
from pathlib import Path

import pytest

from intent_runtime.handoff import copy_handoff, read_json, source_identity, validate_calibration, validated_length


def write_handoff(root: Path, source='kev-tuned'):
    checkpoint = root / 'selected'
    checkpoint.mkdir(parents=True)
    (checkpoint / 'head.pt').write_bytes(b'fixture checkpoint head')
    (checkpoint / 'adapter.safetensors').write_bytes(b'fixture adapter')
    (checkpoint / 'selected.json').write_text(json.dumps({'source': source, 'candidate': 'fixture'}))
    (root / 'calibration.json').write_text(json.dumps({'M1': {'T': 2.0, 'b': .25}}))
    (root / 'long_context.json').write_text(json.dumps({'validated_length': 16384, 'measurement': 'fixture'}))
    return checkpoint


def test_strict_calibration_accepts_serving_option_keys():
    parameters = {'M1': {'T': 1, 'b': 0}, 'D5': {'T': .8, 'b': {'0': -.1, '1': 0, '2': .1}},
                  'G2': {'T': 2, 'b': {'done': 0, 'broken': .2, 'not done': -.1, "can't tell from the evidence": 0}}}
    validate_calibration(parameters)
    assert parameters['D5']['T'] == .8


@pytest.mark.parametrize('parameters', [
    {'M1': {'T': .9, 'b': 0}}, {'M1': {'T': 2, 'b': {'true': .1}}},
    {'M1': {'T': math.inf, 'b': 0}}, {'M1': {'T': 2, 'b': True}},
    {'M1#E2': {'T': 2, 'b': 0}}, {'M1~neg': {'T': 2, 'b': 0}},
    {'D5': {'T': 2, 'b': {'0': 0, '1': 0}}},
    {'D5': {'T': 2, 'b': {'0': 0, '1': math.nan, '2': 0}}},
    {'M1': {'T': 2, 'b': 0, 'unknown': 1}},
])
def test_malformed_calibration_is_rejected(parameters):
    with pytest.raises(ValueError):
        validate_calibration(parameters)


@pytest.mark.parametrize('record', [{}, {'length': 8192}, {'L': True}, {'L': 8192.0}, {'L': 0},
                                   {'L': 8192, 'validated_length': 16384}])
def test_length_requires_unambiguous_semantic_integer_key(record):
    with pytest.raises(ValueError):
        validated_length(record)


def test_matching_length_aliases_preserve_the_reported_length():
    assert validated_length({'L': 32768, 'validated_length': 32768, 'other': 'kept'}) == 32768


def test_source_identity_never_guesses_or_overrides_conflicts():
    assert source_identity({'source': 'stock-kev'}) == 'stock-kev'
    assert source_identity({}, 'kev-tuned') == 'kev-tuned'
    for metadata, explicit in [({}, None), ({'source': 'unknown'}, None), ({'source': 'stock-kev'}, 'kev-tuned')]:
        with pytest.raises(ValueError):
            source_identity(metadata, explicit)


def test_json_duplicate_keys_and_nonfinite_constants_are_rejected(tmp_path):
    path = tmp_path / 'metadata.json'
    for value in ['{"L":8192,"L":32768}', '{"L":NaN}', '[]']:
        path.write_text(value)
        with pytest.raises(ValueError):
            read_json(path)


@pytest.mark.parametrize('missing', ['selected/head.pt', 'calibration.json', 'long_context.json'])
def test_missing_handoff_never_changes_the_target(tmp_path, missing):
    source, target = tmp_path / 'training', tmp_path / 'runtime'
    write_handoff(source)
    (source / missing).unlink()
    target.mkdir()
    pointer = target / 'selected.json'
    pointer.write_bytes(b'old pointer bytes')
    with pytest.raises(FileNotFoundError):
        copy_handoff(source, target, 'new-checkpoint')
    assert pointer.read_bytes() == b'old pointer bytes'
    assert list(target.iterdir()) == [pointer]


def test_malformed_handoff_never_changes_the_target(tmp_path):
    source, target = tmp_path / 'training', tmp_path / 'runtime'
    write_handoff(source)
    (source / 'long_context.json').write_text('{"L":8192,"validated_length":32768}')
    with pytest.raises(ValueError):
        copy_handoff(source, target, 'new-checkpoint')
    assert not target.exists()


def test_fresh_version_layout_preserves_selection_metadata_and_old_weights(tmp_path):
    source, target = tmp_path / 'training', tmp_path / 'runtime'
    checkpoint = write_handoff(source)
    metadata = (checkpoint / 'selected.json').read_bytes()
    old = target / 'selected/old/checkpoint'
    old.mkdir(parents=True)
    (old / 'stale-shard.safetensors').write_bytes(b'old weights stay here')
    (target / 'selected.json').write_text(json.dumps({'checkpoint': str(old)}))
    receipt = copy_handoff(source, target, 'new-checkpoint')
    pointer = read_json(target / 'selected.json')
    assert pointer == receipt['selected']
    assert pointer['source'] == 'kev-tuned'
    destination = target / 'selected/new-checkpoint'
    assert Path(pointer['checkpoint']) == destination / 'checkpoint'
    assert Path(pointer['calibration']) == destination / 'calibration.json'
    assert (destination / 'checkpoint/selected.json').read_bytes() == metadata
    assert not (destination / 'checkpoint/stale-shard.safetensors').exists()
    assert (old / 'stale-shard.safetensors').read_bytes() == b'old weights stay here'
    assert (destination / 'long_context.json').read_bytes() == (source / 'long_context.json').read_bytes()
    assert receipt['validated_length'] == 16384
    assert (checkpoint / 'selected.json').read_bytes() == metadata


def test_existing_version_is_not_overwritten(tmp_path):
    source, target = tmp_path / 'training', tmp_path / 'runtime'
    write_handoff(source)
    version = target / 'selected/existing'
    version.mkdir(parents=True)
    (version / 'marker').write_text('unchanged')
    with pytest.raises(FileExistsError):
        copy_handoff(source, target, 'existing')
    assert (version / 'marker').read_text() == 'unchanged'
    assert not (target / 'selected.json').exists()
