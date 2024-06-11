ARG VM_BASE
FROM $VM_BASE

ARG VM_USER
ARG VM_HOME
ARG VM_CODE
ARG PROJ_INIT_FOLD

# COPY --exclude=app/ ./search_app VM_CODE/
# COPY ./search_app $VM_CODE/search_app

WORKDIR $VM_HOME/

COPY $PROJ_INIT_FOLD/requirements.txt './requirements.txt'

RUN apt-get update\
    && apt-get install sudo \
    && apt-get install -y chromium-driver

RUN pip3 install --no-cache-dir -r  requirements.txt\
    && apt-get clean autoclean\
    && apt-get autoremove --yes\
    && rm -rf /var/lib/{apt,dpkg,cache,log}

# RUN apk add --no-cache sudo \
#     && apk add --no-cache --virtual .build-deps gcc musl-dev g++ linux-headers\
#     py3-clang\
#     openjpeg-dev \
#     jpeg-dev \
#     swig \
#     make \
#     clang-dev\
#     && pip3 install --no-cache-dir -r  requirements.txt\
#     && apk add --no-cache chromium-chromedriver

RUN adduser --disabled-password --gecos '' $VM_USER \
  && adduser $VM_USER sudo \
  && echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers \
  && chown -R $VM_USER $VM_HOME

# RUN python -m nltk.downloader stopwords

# RUN python -m nltk.downloader stopwords

RUN python -m nltk.downloader -d '/usr/local/nltk_data' 'stopwords' 'words'

# RUN python3 -c <<HEREDOC\
# import nltk\
# nltk.download('stopwords')\
# HEREDOC

USER $VM_USER


WORKDIR $VM_HOME

COPY $PROJ_INIT_FOLD/entrypoint.sh ./
RUN sudo chmod +x ./entrypoint.sh

WORKDIR $VM_CODE

ENTRYPOINT /home/docker/entrypoint.sh