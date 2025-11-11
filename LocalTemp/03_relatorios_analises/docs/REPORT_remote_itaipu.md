# Remote Itaipu Utility Overview

File: `utils/remote_itaipu.py`

- Sync: `fetch_pending_ssas`, `fetch_ssa_detail`
- Async: `fetch_pending_ssas_async`, `fetch_ssa_detail_async`
- Options: timeout, SSL verify toggle, retries/backoff
- Helpers: `filter_by_executors`, `map_to_dataframe`, `to_json_pretty`

Usage recommendations:
- Keep `verify_ssl=True` in production.
- Limit years and ranges to reduce payloads.
- Consider caching results when appropriate.
