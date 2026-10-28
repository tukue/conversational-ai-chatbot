FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SHARE=false
ENV GRADIO_DEBUG=false
ENV HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

COPY requirements.txt requirements-proxy.txt ./
RUN python -m pip install --no-cache-dir \
        --index-url https://pypi.org/simple \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch==2.3.1+cpu" \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY --chown=10001:10001 . .

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app \
    && mkdir -p /home/app/.cache/huggingface \
    && chown -R 10001:10001 /home/app

USER 10001:10001

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/', timeout=3)"

CMD ["python", "app.py"]
