FROM python:3.7-alpine
ENV FLASK_ENV "development"
ENV HOST "0.0.0.0"
ENV PORT "8080"
ENV SRC "main.py"

COPY . /hw4
WORKDIR /hw4/src
RUN pip install flask-restful requests gunicorn

ENTRYPOINT gunicorn -c /hw4/config.ini main:app 
