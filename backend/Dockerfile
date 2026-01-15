# Usa uma imagem leve do Python 3.11
FROM python:3.11-slim

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema (necessário para drivers do Postgres)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências primeiro (para cachear a instalação)
COPY requirements.txt .

# Instala as libs do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código
COPY . .

# Comando para rodar a API (Baseado no seu VS Code launch.json)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]