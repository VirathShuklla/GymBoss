FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN grep -v '^emergentintegrations' requirements.txt > req.txt && pip install --no-cache-dir -r req.txt
COPY . .
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/api/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2", "--proxy-headers"]
