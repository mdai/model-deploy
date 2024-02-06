{{PARENT_IMAGE}}

WORKDIR /src
ARG MDAI_PATH

{{ENV}}

COPY requirements.txt lib/${MDAI_PATH}/*.whl /src/
COPY lib/${MDAI_PATH}/requirements.txt /src/mdai-requirements.txt

RUN /bin/bash -c "pip install -r requirements.txt && \
    pip install -r mdai-requirements.txt"

COPY server.py /src/
COPY validation.py /src/
ENV MDAI_PATH=${MDAI_PATH}

{{COPY}}

RUN useradd docker
USER docker

EXPOSE 6324

{{COMMAND}}
