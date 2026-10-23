FROM python:3.11.17-slim

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" \
    && python -m pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python scripts/init_db.py && python scripts/seed_charities.py
EXPOSE 5000
CMD ["python", "app.py"]
