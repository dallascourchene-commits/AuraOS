# AuraOS Public Demo Application Platform

## What the submission field means

A **demo application platform** is the hosting/runtime service that lets judges open and use the project. It is separate from the slide deck, video, and source repository.

For AuraOS, enter:

```text
Hugging Face Spaces (Docker)
```

After deployment, enter the public application URL printed by the deployment script:

```text
https://<hugging-face-user>-<space-name>.hf.space
```

Do not enter `127.0.0.1` or `localhost` as the public application URL.

## Why this platform fits AuraOS

- Runs the existing custom Python/HTML/JavaScript application as a Docker container.
- Gives judges a public browser URL.
- Does not require the demo to be rewritten in Gradio or Streamlit.
- Supports private runtime secrets for Fireworks and optional Direct DeepSeek access.
- Runs the deterministic demo on free CPU hardware; external model calls remain optional.

## Deploy from Windows PowerShell

From the AuraOS repository root:

```powershell
python -m pip install "huggingface_hub>=0.36,<2"
hf auth login
python scripts/deploy_huggingface_space.py --space-id YOUR_HF_USERNAME/auraos-demo
```

The script creates or updates a public Docker Space and prints:

- the Space repository URL;
- the deployment commit URL;
- the public `hf.space` application URL.

Wait for the Space status to become **Running**, then open the public application URL in a private/incognito browser window.

## Configure Fireworks without exposing the key

In the Space:

1. Open **Settings**.
2. Open **Variables and secrets**.
3. Add a **Secret** named `FIREWORKS_API_KEY`.
4. Paste the Fireworks key into the secret value field.
5. Optionally add `DEEPSEEK_API_KEY` as a direct-provider fallback.
6. Restart the Space.

Do not upload `aura_secrets.json`, `.env`, terminal screenshots containing values, or API keys to either GitHub or Hugging Face.

The deterministic intent compiler, topology, Civic demo, Human Agent workflow, Observatory, and Learning Arena remain demonstrable when no model secret is configured.

## Verify before submission

Open the public URL while logged out and verify:

1. the four Arena tabs load;
2. the Winnipeg synthetic-data notice is visible;
3. the Observatory compiles an ordinary intention;
4. the Human Agent guided gates and topology load;
5. the Attempt Archive is inspectable;
6. the Learning Arena is identified as the Crucible;
7. no key, token, private path, or personal data appears;
8. no action automatically commits, pushes, opens a PR, or merges.

## Submission entries

```text
Demo application platform: Hugging Face Spaces (Docker)
Application URL: https://<hugging-face-user>-auraos-demo.hf.space
Repository: https://github.com/dallascourchene-commits/AuraOS
Local fallback platform: Docker / Local Web Application
```

## Source and image boundary

The Space Dockerfile checks out the reviewed AuraOS commit named in `deploy/huggingface-space/Dockerfile`. This makes the public demonstration reproducible and prevents an unrelated future repository change from silently altering the judged build.

The Space contains only a Dockerfile and app card. It does not contain Aura secrets. Runtime secrets are injected by the hosting platform and are never copied into the image or repository.
