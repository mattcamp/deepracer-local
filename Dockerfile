FROM python:3-slim

COPY requirements.txt requirements.txt
RUN pip3 install -U -r requirements.txt

CMD ["flask","run"]