# Web setup

Once `rp5-llm-ui.service` is running, open `http://127.0.0.1:8080/setup` on the device. The kiosk URL is loopback on purpose: the setup code is shown only to a local browser. A laptop on the LAN has to type the code from the handheld screen.

The wizard asks for:

- the measured hardware check
- one SSH public key, never a private key
- a model id from `config/models.yaml`
- CPU, experimental Vulkan, or auto
- whether the gateway may listen on the LAN
- a hostname

Install writes that plan. It does not accept a shell command. llama.cpp installation stays blocked until that installer exists. A model whose checksum is empty is not downloaded.

Finish locks the install routes. Unlock is only accepted from loopback, with the setup code and the confirmation string `unlock`.

Applying a hostname or installing the public key into `~/.ssh` is done by `rp5-llm-setup.service`, which runs `python -m rp5_llm.apply` as a fixed set of arguments. Preview those commands with `python -m rp5_llm.apply --dry-run`.

Default API exposure is local. LAN exposure restarts the management process on `0.0.0.0`. llama-server stays on `127.0.0.1:8081`.
