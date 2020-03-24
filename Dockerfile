FROM python:3-slim

RUN pip3 install -U docker docker-compose Flask python-dotenv flask-sqlalchemy flask-wtf
COPY manager.py manager.py
CMD ["python3","manager.py"]