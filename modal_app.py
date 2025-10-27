from modal import App, Image, Mount, asgi_app, Secret
import os

image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
        "fastapi", "uvicorn", "jinja2", "python-multipart",
        "pydantic", "numpy", "pandas", "regex", "cryptography", "markdown"
    )
)

repo_mount = Mount.from_local_dir(".", remote_path="/app", condition=lambda p: ".git" not in p)
app = App("logsense-native")

def _load_fastapi():
    os.environ.setdefault("LOGSENSE_WEB_MODE", "modal")
    try:
        from web_http_app import app as logsense_app
        return logsense_app
    except Exception:
        pass
    # Uncomment this block if your app uses create_app()
    # try:
    #     from web_http_app import create_app
    #     return create_app()
    # except Exception:
    #     pass
    raise RuntimeError("Could not import FastAPI app. Check _load_fastapi().")

@asgi_app(image=image, mounts=[repo_mount], secrets=[Secret.from_name("logsense_env")])
def fastapi_app():
    return _load_fastapi()
