# Sidequests

| ID | Status | Sidequest | Goal-directed chain | Exit evidence | Budget / fallback | Return |
|---|---|---|---|---|---|---|
| access | done | Restore GitHub DNS and synchronize without disturbing training edits. | Access recovery -> source clone and repository publication -> setup -> live service. | Kev HEAD matches the pin; isolated pull and authorized push succeeded. | Two repair commits. Fallback: isolated checkout and connector source inspection while DNS recovers. | TASKLIST.md:L5 |
| log-evidence | done | Correct serving log collection. | Measured raw probabilities -> calibration serving gate -> live classifier. | Serving audit matches independent calibration math. | One repair commit; fallback: explicit CLI log fetch. | TASKLIST.md:L6 |
| warmup-teeth | done | Prove warmup rejection on dev and restore. | Deliberate bad return -> rejecting driver -> required warmup gate -> live service. | Wrong return rejected and original deployment warmed. | One mutation and restoration; fallback restores original app bytes. | TASKLIST.md:L6 |
