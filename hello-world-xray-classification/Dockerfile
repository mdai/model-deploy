FROM python:3.7.5

WORKDIR /src

COPY requirements.txt /src/
RUN pip install -r requirements.txt

COPY model.h5 server.py /src/

RUN useradd docker
USER docker

EXPOSE 6324

CMD ["python", "server.py"]
