FROM python:3.11-slim

# Instalação do Java (Necessário para a biblioteca tabula-py processar o PDF)
RUN apt-get update && \
    apt-get install -y default-jre && \
    apt-get clean

# Define o diretório de trabalho do contêiner
WORKDIR /app

# Copia e instala apenas os requisitos primeiro (aproveita cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto para o contêiner
COPY . .

# Expõe a porta 5000 (porta padrão do Flask)
EXPOSE 5000

# Variáveis de ambiente padrão para o Flask
ENV FLASK_APP=app.py

# Comando para rodar o aplicativo, expondo para qualquer IP externo
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
