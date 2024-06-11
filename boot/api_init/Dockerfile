ARG VM_BASE
FROM $VM_BASE

ARG VM_USER
ARG VM_HOME
ARG VM_CODE
ARG VM_HOST_PIP
ARG PROJ_INIT_FOLD

COPY $VM_HOST_PIP ./

RUN apt-get update\
    && apt-get install sudo \
    && pip3 install --no-cache-dir -r  requirements.txt\
    && apt-get clean autoclean\
    && apt-get autoremove --yes\
    && rm -rf /var/lib/{apt,dpkg,cache,log}

# RUN apk update \
# && apk add --no-cache sudo \
# && apk add --no-cache --virtual .build-deps gcc musl-dev g++\
# && apk add libffi-dev\
# && pip3 install --no-cache-dir -r ./requirements.txt \
# && apk del .build-deps

### DEV
# COPY --exclude=*tasks/* --exclude=*celery.py ./search_app VM_CODE
# COPY ./search_app $VM_CODE/search_app


# RUN apk add --no-cache bash

RUN adduser --disabled-password --gecos '' $VM_USER \
    && adduser $VM_USER sudo \
    && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
    && chown -R $VM_USER $VM_HOME

# RUN adduser --disabled-password --gecos '' $VM_USER \
#     && addgroup sudo \
#     && adduser $VM_USER sudo \
#     && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
#     && chown -R $VM_USER $VM_HOME

USER $VM_USER

WORKDIR $VM_HOME

COPY $PROJ_INIT_FOLD/entrypoint.sh ./
RUN sudo chmod +x ./entrypoint.sh

WORKDIR $VM_HOME

EXPOSE 80
ENTRYPOINT ./entrypoint.sh