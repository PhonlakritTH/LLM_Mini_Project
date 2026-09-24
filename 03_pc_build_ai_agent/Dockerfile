FROM python:3.12-slim
RUN useradd -m -u 10001 agent
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
USER agent
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8100"]
