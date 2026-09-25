# LLM runtime

llama.cpp remains the inference engine. The unit `rp5-llm.service` starts `/opt/rp5-llm/bin/llama-server` on `127.0.0.1:8081` only when that binary exists. The unit ships disabled.

Clients that want an OpenAI-compatible API talk to the management process at `/v1/*`. That process forwards the body and reads token counts from the `usage` object. Prompt text is not written to the history database unless `RP5_LLM_CAPTURE_CONTENT=true`.

CPU is the default backend. `auto` also reports CPU until a benchmark file records a winner. Vulkan can be selected in the wizard and is labeled experimental.

The management `/health` endpoint stays successful when llama.cpp is down, so the dashboard can boot first and show `offline`. `/api/status` is the appliance view: it reports `online` only when llama.cpp answers `/health`.
