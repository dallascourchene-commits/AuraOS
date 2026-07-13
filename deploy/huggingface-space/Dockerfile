FROM python:3.11-slim

ARG AURA_REPO=https://github.com/dallascourchene-commits/AuraOS.git
ARG AURA_REF=611f80b9725a9b6f103e77f2849f6f90ee034836

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/user \
    PORT=7860

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

RUN git clone --depth 1 --branch main "${AURA_REPO}" . \
    && git fetch --depth 1 origin "${AURA_REF}" \
    && git checkout --detach "${AURA_REF}" \
    && rm -rf .git

RUN python -m pip install --no-cache-dir \
    "numpy>=1.26.4,<3.0" \
    "websockets>=12.0,<17.0" \
    "aiosqlite>=0.20.0,<1.0" \
    "ddgs>=6.0,<10.0" \
    "wasmtime>=20.0,<46.0" \
    "aiohttp>=3.9.0,<4.0" \
    "beautifulsoup4>=4.12.0,<5.0" \
    "httpx>=0.27.0,<1.0" \
    "cryptography>=41.0.0,<45.0"

RUN mkdir -p Aura_Memory Aura_Staging \
    && chown -R user:user /home/user/app

USER user
EXPOSE 7860

CMD ["python", "aura_showcase_server.py", "--host", "0.0.0.0", "--port", "7860", "--demo-project", "winnipeg_pathways"]
