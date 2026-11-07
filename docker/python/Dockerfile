{{PARENT_IMAGE}}

WORKDIR /src
ARG MDAI_PATH

{{ENV}}

# The deeplearning-platform images stopped shipping conda from release m129 on (base-cpu and
# base-cu122 and newer). Install Miniforge where it is missing so every base image can create the
# model's env; images that still have conda keep their own. The base images are x86_64 only.
ARG MINIFORGE_VERSION=26.7.2-1
ARG MINIFORGE_SHA256=cf0df84220e1c83a1cb2f447056594ca458fa4c6a353430c498f281ec21bd187
ENV PATH=/opt/conda/bin:${PATH}
RUN if ! command -v conda >/dev/null; then \
        curl -fsSL -o /tmp/miniforge.sh \
            "https://github.com/conda-forge/miniforge/releases/download/${MINIFORGE_VERSION}/Miniforge3-${MINIFORGE_VERSION}-Linux-x86_64.sh" && \
        echo "${MINIFORGE_SHA256}  /tmp/miniforge.sh" | sha256sum -c - && \
        bash /tmp/miniforge.sh -b -p /opt/conda && \
        rm /tmp/miniforge.sh && \
        /opt/conda/bin/conda clean -afy; \
    fi

{{CONDA_ENV}}

COPY requirements.txt lib/${MDAI_PATH}/*.whl /src/
COPY lib/${MDAI_PATH}/requirements.txt /src/mdai-requirements.txt
RUN /bin/bash -c "source activate mdai-env && \
    pip install -r requirements.txt && \
    pip install -r mdai-requirements.txt"

COPY server.py /src/
COPY validation.py /src/
ENV MDAI_PATH=${MDAI_PATH}

{{COPY}}

RUN useradd docker
USER docker

EXPOSE 6324

{{COMMAND_MDAI}}
