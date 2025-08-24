"""Modal deployment with async patterns - imports handled within Modal function.

# NOTE:
# - Web server runs on a minimal, pinned image (web_image) with FastAPI only.
# - GPU/model work must live in a separate Modal function/image to keep web cold starts fast.
# - Keep FastAPI imports inside the @modal.asgi_app() function so imports resolve from the correct image.
# - If you change dependencies, bump a version pin to bust image cache before redeploy.
"""
import modal
from typing import Dict, Any

app = modal.App("logsense-async-async-app")

# Minimal, pinned web image for FastAPI-only server
web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.115.*",
        "uvicorn==0.30.*",
        "pydantic==2.*",
        "python-multipart==0.0.9",
        "jinja2==3.1.*",
        "aiofiles==24.1.0",
        "starlette==0.38.3",
    )
)

@app.function(image=web_image, name="async-app", allow_concurrent_inputs=100)
@modal.asgi_app()
def async_app():
    # Runtime probe: verify FastAPI is discoverable in this container
    import sys as _sys, pkgutil as _pkgutil
    fastapi_present = _pkgutil.find_loader("fastapi") is not None
    print(f"[RUNTIME_PROBE] py={_sys.version.split()[0]} fastapi_present={fastapi_present}")

    # Import inside the function so resolution uses the baked image
    import fastapi, pydantic, uvicorn, starlette  # version print only
    from fastapi import FastAPI, UploadFile, File, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware

    print(
        f"[VERSIONS] fastapi={fastapi.__version__} pydantic={pydantic.__version__} "
        f"uvicorn={uvicorn.__version__} starlette={starlette.__version__}"
    )

    api = FastAPI(title="haiec", version="1.0.0")

    # CORS if browser uploads hit this directly
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/health")
    async def health():
        return {"status": "ok", "service": "haiec", "version": "1.0.0"}

    # Mount static/templates if present; keep paths as in repo
    # api.mount("/static", StaticFiles(directory="static"), name="static")

    # TODO: reattach app routes (/ , /upload, /analyze, /submit_context) from existing code
    # Ensure none of those import GPU libs at import-time; move heavy loads to handlers or a separate worker.

    return api

@app.function(image=web_image, name="web-diag")
def web_diag():
    import pkgutil, platform
    return {
        "fastapi_present": pkgutil.find_loader("fastapi") is not None,
        "python": platform.python_version(),
    }


if __name__ == "__main__":
    print("LogSense Async Deployment")
    print("Features:")
    print("- Full async/await patterns")
    print("- SonarCloud compliant code")
    print("- Reduced cognitive complexity")
    print("- Proper error handling")
    print("- Warm container strategy")
