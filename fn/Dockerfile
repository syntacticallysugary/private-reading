FROM python:3.12-slim

WORKDIR /function

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY func.py .

ENTRYPOINT ["fdk", "func.py", "handler"]
