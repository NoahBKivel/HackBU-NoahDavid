# Agent concurrency verification

The installed app server recognizes
`agents.max_concurrent_threads_per_session`. Official documentation states
that this value limits spawned threads, excluding the primary agent:
https://learn.chatgpt.com/docs/agent-configuration/subagents#global-settings.

The saved user configuration was changed from 6 to 100. A fresh process of
the same installed app-server binary returned an effective value of 100
through `config/read`, with the user configuration as its source and no
overriding project layer. The result is saved in
`results/agent-limit-verification.json`. The probe created no thread and
made no model call.

A probe under the restricted sandbox did not load the owner's user
configuration and returned no agent setting. The authorized host process
loaded the correct user layer and passed. Restart verification must use
the same host identity as the application.

The running conversation still advertises seven total slots. Fully quit
and reopen Codex, then resume the existing task, to reload the configured
limit. The next session must execute task.md Section 0 before resuming.

Active task anchor: TASKLIST.md:L15
