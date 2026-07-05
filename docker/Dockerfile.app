FROM python:3.12.3-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir uv
RUN uv pip install --system --no-cache -r requirements.txt

COPY acos_client/ ./acos_client/
COPY acos_models/ ./acos_models/
COPY streamlit_app.py .

CMD ["streamlit", "run", "streamlit_app.py"]
