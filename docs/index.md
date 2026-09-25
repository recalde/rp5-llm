# RP5 LLM

A Retroid Pocket 5, upstream Linux, and llama.cpp. The result is a small machine that serves a local model.

```text
Retroid Pocket 5
+
Linux
+
llama.cpp
=
portable local AI appliance
```

Android stays on the internal storage. The SD card boots upstream [Pocknix](https://github.com/shuuri-labs/pocknix-os). This project adds the management service, the dashboard, and the setup plan. It does not fork Pocknix and it does not flash a bootloader.

[Get started](getting-started.md) · [Install](flashing.md) · [Web setup](web-setup.md) · [API](api.md) · [GitHub](https://github.com/recalde/rp5-llm)

## Download

The SD card image is the latest Pocknix build for SM8250, checked against the pin in the repository before `scripts/flash-sd.sh` writes it:

[Pocknix releases](https://github.com/shuuri-labs/pocknix-os/releases/latest)

<p id="rp5-release">Project releases will be listed here after the first tag.</p>
<script>
fetch("https://api.github.com/repos/recalde/rp5-llm/releases/latest")
  .then(function (response) { return response.ok ? response.json() : Promise.reject(); })
  .then(function (data) {
    var node = document.getElementById("rp5-release");
    if (!data.html_url || data.html_url.indexOf("https://github.com/recalde/rp5-llm/") !== 0) {
      return;
    }
    var link = document.createElement("a");
    link.href = data.html_url;
    link.textContent = "Latest project release " + (data.tag_name || "");
    node.replaceChildren(link);
  })
  .catch(function () {});
</script>
