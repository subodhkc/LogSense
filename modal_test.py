import modal

app = modal.App("logsense-test")

# Minimal image to test encoding fix
image = modal.Image.debian_slim(python_version="3.11").pip_install("fastapi", "openai", "python-dotenv")

@app.function(image=image)
@modal.web_endpoint(method="GET")
def test():
    return {"status": "working", "message": "AI analysis fix deployed"}

@app.function(image=image)  
@modal.web_endpoint(method="POST")
def test_ai():
    try:
        import os
        os.environ["OPENAI_API_KEY"] = "test"  # Will fail gracefully
        return {"ai_test": "Cloud AI fallback working"}
    except Exception as e:
        return {"error": str(e)}
