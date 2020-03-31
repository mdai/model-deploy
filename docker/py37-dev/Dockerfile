FROM python:3.7.6

WORKDIR /src

COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY ./model-requirements.txt /src/model-requirements.txt
RUN pip install -r model-requirements.txt

COPY server.py /src/
COPY main.sh /src/
COPY validation.py /src/

RUN ["chmod", "+x", "/src/main.sh"]
RUN apt-get update
RUN apt-get install -y inotify-tools
RUN useradd docker
USER docker

EXPOSE 6324

CMD ["./main.sh", "/src/lib"]
