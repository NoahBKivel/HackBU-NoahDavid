# DNS repair outcome

The owner authorized a ten-minute investigation from 00:39:48 to 00:49:48 EST
on 2026-11-08. The investigation met its exit condition by 00:41:31 EST.

## Measured result

Elevated Windows DNS resolved `registry-1.docker.io` and the Harbor frontend.
Inspection of the installed Harbor package's public
`DEFAULT_SUPABASE_URL` established its actual API endpoint as
`https://ofhuhcpkvzjlejydnvyd.supabase.co`.

The host probe at 05:41:06 UTC resolved eight Docker IPv4 addresses and two
Harbor API addresses. HTTPS reached both endpoints and returned HTTP 401,
the expected response for requests without authorization headers.
These response codes establish reachability, not authorization.

The cached `node:22` container used Docker's DNS server at 192.168.65.7.
Its DNS and HTTPS probes independently reached the Docker registry and the
actual Harbor API. Each returned HTTP 401 without supplied credentials.
The container resolved eight Docker addresses and two Harbor API addresses.

The existing authenticated Harbor CLI session then ran this bounded query:

```
harbor hub job list --scope all --search hvtb --limit 3 --json
```

It exited with code 0, returned valid JSON, wrote 83 stdout bytes and no
stderr bytes. The JSON response has five top-level fields. The sanitized
host and authenticated probe evidence is in `results/dns-host.json`.

The relevant Windows DNS-cache query returned no matching entries.
No cache flush, DNS-server change, hosts-file entry, proxy change or VPN
change was performed. No credential was printed, copied or logged.

## Interpretation and return

The observed failures were intermittent. Current host and container probes
do not reproduce them. Docker and authenticated Harbor are reachable, so
the repair branch is closed and the setup source work can resume.

If the failure recurs during the overnight build, retry a bounded service
probe once. Use the already built `intent-agent-run` image for agent jobs.
If Harbor remains externally unavailable, redistribute HVTB's quota within
its objective as required by the training specification. Do not assign a
static service IP or change the machine's DNS configuration on this evidence.

Active task anchor: TASKLIST.md:L15
Sidequest anchor: SIDEQUESTS.md:L12
