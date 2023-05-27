FROM python:3.11-slim

RUN apt update -y && \
    apt install -y --no-install-recommends \
    make wget

WORKDIR /app
COPY . /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
EXPOSE 8456

RUN make install

ENTRYPOINT ["make", "start"]
