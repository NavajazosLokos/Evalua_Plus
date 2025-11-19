FROM python:3.11-slim

WORKDIR /app

# Copiar todo el contenido del backend
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary sqlalchemy

# Ejecutar uvicorn usando módulo completo para evitar errores de imports relativos
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]