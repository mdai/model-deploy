FROM python:3.7.6

WORKDIR /src
ARG MDAI_PATH

COPY requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

COPY ./model-requirements.txt /src/model-requirements.txt
RUN pip install -r model-requirements.txt

COPY ./mdai-requirements.txt /src/mdai-requirements.txt
RUN pip install -r /src/mdai-requirements.txt

COPY server.py /src/
COPY main.sh /src/
COPY validation.py /src/

RUN ["chmod", "+x", "/src/main.sh"]
RUN apt-get update
RUN apt-get install -y inotify-tools

ENV MDAI_PATH=${MDAI_PATH}
RUN useradd docker
USER docker

EXPOSE 6324
CMD ["sh", "-c", "./main.sh /src/lib /src/lib/$MDAI_PATH"]
