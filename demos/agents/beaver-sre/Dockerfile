# One run of the convention-swap agent, as a container.
#
# Both instrumentation libraries are installed in the image so the same image can run
# either convention — the choice is CAPYBARA_INSTRUMENTATION at run time, not build
# time. Two images would let them drift, and then a difference in the spans would no
# longer be attributable to the convention.
FROM python:3.12-slim

WORKDIR /app

# Requirements first, so a prompt or code change does not reinstall the world.
COPY requirements.txt .
RUN pip install --no-cache-dir -q -r requirements.txt

COPY telemetry.py db.py tools.py agent.py app.py service.py ./

# Unbuffered, or kubectl logs shows nothing until the process exits.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# The service by default: two of these run side by side in the cluster and the console
# triggers them. Override the command with app.py for the one-shot CLI.
ENTRYPOINT ["python", "service.py"]
