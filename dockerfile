FROM python:3.7-alpine
ENV FLASK_ENV "development"
ENV HOST "0.0.0.0"
ENV PORT "8080"
ENV SRC "main.py"

COPY . /Sharded-Key-Value-Store
WORKDIR /Sharded-Key-Value-Store/src
RUN pip install flask-restful requests gunicorn

ENTRYPOINT gunicorn -c /Sharded-Key-Value-Store/config.ini main:app 
