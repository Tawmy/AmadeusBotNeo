FROM python:3.9-slim
COPY ./src .
RUN apt-get update && apt-get install -y libpq-dev gcc
RUN pip install -r ./requirements.txt
CMD [ "python", "./amadeus.py" ]
