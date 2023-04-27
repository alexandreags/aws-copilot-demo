FROM python:3.10.10-slim-buster
WORKDIR /app
COPY producer-sqs.py /app
COPY requirements.txt /app
RUN pip install -r requirements.txt
EXPOSE 8081
CMD [ "python", "producer-sqs.py"]
