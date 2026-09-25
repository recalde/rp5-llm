# Models

`config/models.yaml` is the allow list. The wizard rejects any other id.

Each entry names a repository, a filename, an approximate RAM and disk size, and a sha256. While the checksum is empty, the setup step returns `blocked` and nothing is downloaded. When a checksum is pinned, the setup service may download that one file and keep it only if the hash matches.

The current entries are a small and a medium Qwen2.5 Instruct GGUF. Their checksums are intentionally empty until they are verified and committed. Weights are never stored in git.

History keeps at most 1000 requests or 7 days, whichever bound is reached first. Those limits are `RP5_LLM_HISTORY_LIMIT` and `RP5_LLM_HISTORY_DAYS`.
