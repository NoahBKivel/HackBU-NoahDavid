"""Check linked-record partitioning for replicated global optimizer groups."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from intent_training.kevpatch.distributed_ddp import rank_records


def test_rank_partition_preserves_linked_units_and_all_records():
    records = [{'_meta': {'id': str(index)}} for index in range(16)]
    records[0]['_meta']['pair_id'] = records[8]['_meta']['pair_id'] = 'pair'
    records[8]['_meta']['sibling_group'] = records[15]['_meta']['sibling_group'] = 'siblings'
    shards = rank_records(records, 4)
    assert sorted(id(record) for shard in shards for record in shard) == sorted(map(id, records))
    locations = {id(record): index for index, shard in enumerate(shards) for record in shard}
    assert locations[id(records[0])] == locations[id(records[8])] == locations[id(records[15])]
    assert rank_records(records, 4) == shards


def test_partial_global_group_keeps_empty_rank_shards():
    records = [{'_meta': {'id': 'only'}}]
    assert rank_records(records, 4) == [records, [], [], []]
