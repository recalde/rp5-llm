# Development

Cursor Remote SSH is the developer path. It is not required to use the dashboard.

After SSH is enabled on the Pocket:

```bash
./scripts/prepare-ssh.sh deck@DEVICE_IP --write-config
ssh rp5 'git clone https://github.com/recalde/rp5-llm.git ~/workspaces/rp5-llm'
```

In Cursor, use **Remote-SSH: Connect to Host** and open `~/workspaces/rp5-llm`.

Password login stays available until a key login has been checked. Do not disable it first.

Build and preview the documentation site with:

```bash
python3 -m pip install -r requirements-docs.txt
make docs
make docs-serve
```

The device tests are:

```bash
python3 -m pip install -r ui/backend/requirements.txt pytest
make test
```
