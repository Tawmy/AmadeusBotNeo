FROM python:3.9-slim
COPY ./src ./usr/src/bot
WORKDIR ./usr/src/bot
RUN apt-get update && apt-get install -y --no-install-recommends python3-dev=3.7.3-1 libpq-dev=11.9-0+deb10u1 gcc=4:8.3.0-1\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN pip install -r ./requirements.txt
CMD [ "python", "./amadeus.py" ]
