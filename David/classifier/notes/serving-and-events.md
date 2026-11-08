# Serving and event handling

Kev source is pinned to `fc4a17e194bca35a48c57211392ec49ea54a94ac`.
The source was read through GitHub at that revision and from the fetched Git object.

- [api.py](https://github.com/jaredpalmer/kev/blob/fc4a17e194bca35a48c57211392ec49ea54a94ac/kev/api.py)
  preserves question order in `to_record` metadata. Noul options are false, true.
  Choice keys preserve criteria order, and score keys are level indices as strings.
- [serve.py](https://github.com/jaredpalmer/kev/blob/fc4a17e194bca35a48c57211392ec49ea54a94ac/kev/serve.py)
  returns unrounded probability lists from `Server.probs`. `Server.submit` queues a
  Future, so independent RF and screen states can be submitted before waiting.
- [checkpoint.py](https://github.com/jaredpalmer/kev/blob/fc4a17e194bca35a48c57211392ec49ea54a94ac/kev/checkpoint.py)
  sets `model.head.temperature` to `LoadOptions.temperature` when supplied and
  otherwise uses `Checkpoint.meta.temperature`. Loading at temperature 1.0 and
  applying the shipped value in the runtime therefore avoids applying it twice.
- [Modal concurrency](https://modal.com/docs/guide/concurrent-inputs) runs synchronous
  concurrent inputs on separate threads. The per-session condition protects ordering
  while the model server owns GPU serialization.
- [Modal Dicts](https://modal.com/docs/guide/dicts) persist across redeployments.
  Changes to a retrieved mutable value require an explicit write back. The runtime
  stores each complete event separately and writes its header after event completion.

`Noah/mod/hooks/register.tsx` builds each event with the incremented session sequence
and drains pending items into `new_items`. Its tool event places the denial string
in `action.denied`, or null when the tool was not denied. Turn completion supplies
`agent_text` from the answer and `turn.reason` from the completion event. Shell
deletions must be represented by their command and result because `file_changes`
is produced for Edit and Write rather than inferred from a shell command.

The original placeholder input builder is retained for the independent serving-core
checks. Its lifecycle delegates to the runtime package. It will be removed when the
frozen shared-format binding is installed. No replacement renderer is introduced.
