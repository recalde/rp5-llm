# Architecture

```text
browser or OpenAI client
        │
        ▼
management process   127.0.0.1:8080
        │
        ├── dashboard and setup wizard
        ├── status API
        └── /v1 gateway
                │
                ▼
        llama-server   127.0.0.1:8081
```

The management process records request metadata and serves the screen. llama.cpp runs the model. The gateway is there because llama.cpp's Prometheus metrics are aggregate, and its slot endpoint can contain prompt text.

The engineering decisions, including what the browser cannot do, are in the [design note](design/web-management.md).

Nothing in the normal setup path repartitions internal storage or changes the bootloader. Android remains the recovery path back to the stock menu.
