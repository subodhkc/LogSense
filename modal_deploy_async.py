# modal_deploy_async.py — canonical web entry for https://haiec--logsense-async-async-app.modal.run/
import modal

app = modal.App("logsense-async")  # keep app name; keep URL domain stable

# Minimal pinned web image that DEFINITELY includes FastAPI stack
web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.115.2",
        "starlette==0.38.3",
        "uvicorn==0.30.6",
        "pydantic==2.8.2",
        "python-multipart==0.0.9",
        "jinja2==3.1.4",
        "aiofiles==24.1.0"
    )
)

BUILD_CANARY = "ASGI_FIX_2025-08-24T13:45:00Z"  # unique marker to prove deploy

# Bind the exact endpoint you're hitting: function name must be "async-app"
@app.function(image=web_image, name="async-app")
@modal.asgi_app()
def async_app():
    # Canary + probe BEFORE importing fastapi (must print on every cold start)
    import os, sys, pkgutil, platform
    print(
        f"[CANARY] {BUILD_CANARY} app='logsense-async' func='async-app' "
        f"py={platform.python_version()} "
        f"fastapi_present={pkgutil.find_loader('fastapi') is not None} "
        f"pid={os.getpid()}"
    )

    try:
        from fastapi import FastAPI
        import starlette, pydantic, uvicorn
        print(
            f"[VERSIONS] fastapi>ok pydantic={pydantic.__version__} "
            f"uvicorn={uvicorn.__version__} starlette={starlette.__version__}"
        )
    except Exception as e:
        print(f"[FASTAPI_IMPORT_FAIL] {e!r}")
        import subprocess
        out = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
        print("[PIP_FREEZE_HEAD]\n" + out[:2000])
        raise

    api = FastAPI(title="haiec", version="1.0.0")

    @api.get("/health")
    async def health():
        return {"status": "ok", "service": "haiec", "version": "1.0.0", "canary": BUILD_CANARY}

    return api

# Retire ALL other ASGI exports in THIS file to avoid graph conflicts
if False:
    @app.function()
    @modal.asgi_app()
    def old_async_app():
        ...
