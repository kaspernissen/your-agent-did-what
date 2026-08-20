# otter-sre as a container.
#
# One image, one instrumentation library: requirements.txt installs OpenLLMetry and nothing
# else, so what this image emits is decided at build time and cannot drift at run time.
FROM python:3.12-slim

WORKDIR /app

# Requirements first, so a prompt or code change does not reinstall the world.
COPY requirements.txt .
RUN pip install --no-cache-dir -q -r requirements.txt

COPY telemetry.py db.py mcp_db.py tools.py agent.py app.py service.py ./

# Unbuffered, or kubectl logs shows nothing until the process exits.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# The service by default; the capybara-sre console triggers it. Override with app.py for
# the one-shot CLI.
ENTRYPOINT ["python", "service.py"]
