FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Download spaCy NLP model
RUN python -m spacy download en_core_web_sm

# Copy application code and knowledge base source data
COPY app/ ./app/
COPY knowledge_base/ ./knowledge_base/

# Create required directories
RUN mkdir -p data knowledge_base/indices

# Build the vector knowledge base during image build
# Uses all-MiniLM-L6-v2 for speed (~5 min vs 2+ hours for PubMedBert)
# Set EMBEDDING_MODEL env var to override
ENV EMBEDDING_MODEL=all-MiniLM-L6-v2
RUN python knowledge_base/scripts/build_knowledge_base.py || \
    echo "Warning: Knowledge base build failed — will retry on startup"

# Non-root user for security
RUN useradd -m -u 1000 medcoder && chown -R medcoder:medcoder /app
USER medcoder

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
