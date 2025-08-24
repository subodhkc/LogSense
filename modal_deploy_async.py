# modal_deploy_async.py — canonical web entry for the endpoint at
# https://haiec--logsense-async-async-app.modal.run/

import modal

# Keep the app name so the URL stays identical: ...-logsense-async-async-app
app = modal.App("logsense-async")

# Minimal pinned web image that DEFINITELY contains FastAPI
web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.115.*",
        "starlette==0.38.*",
        "uvicorn==0.30.*",
        "pydantic==2.*",
        "python-multipart==0.0.9",
        "jinja2==3.1.*",
        "aiofiles==24.1.0",
    )
)

# IMPORTANT:
#  - Name the function "async-app" to match the URL segment you are hitting.
#  - Bind it explicitly to web_image.
@app.function(image=web_image, name="async-app")
@modal.asgi_app()
def async_app():
    # Runtime probe BEFORE importing fastapi — proves image contents
    import os, sys, pkgutil, platform
    print(
        f"[RUNTIME_PROBE] app='logsense-async' func='async-app' "
        f"py={platform.python_version()} "
        f"fastapi_present={pkgutil.find_loader('fastapi') is not None} "
        f"pid={os.getpid()}"
    )

    # Now import FastAPI. If it fails, dump pip freeze head to the logs and re-raise.
    try:
        from fastapi import FastAPI
        import starlette, pydantic, uvicorn
        print(
            f"[VERSIONS] fastapi>ok "
            f"pydantic={pydantic.__version__} "
            f"uvicorn={uvicorn.__version__} "
            f"starlette={starlette.__version__}"
        )
    except Exception as e:
        print(f"[FASTAPI_IMPORT_FAIL] {e!r}")
        import subprocess
        out = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True, text=True, check=False
        ).stdout
        print("[PIP_FREEZE_HEAD]\n" + out[:2000])
        raise

    api = FastAPI(title="haiec", version="1.0.0")

    @api.get("/health")
    async def health():
        return {"status": "ok", "service": "haiec", "version": "1.0.0"}

    return api

# Retire any other ASGI exports in THIS file to avoid graph conflicts.
# Keep them for reference only under a dead branch.
if False:
    @app.function()
    @modal.asgi_app()
    def old_async_app():
        ...
