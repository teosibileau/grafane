FROM python:3.6-jessie

# Update packages and install software
RUN apt-get update \
    && apt-get -y install git \
                          python3-dev \
                          python3-pip \
                          libfontconfig \
                          libssl-dev \
                          build-essential \
                          libffi-dev \
                          software-properties-common

RUN pip3 install --upgrade pip

ARG ENV=PROD
ENV DATA_FOLDER=/data

RUN echo "Building image for $ENV environment"

RUN mkdir -p /data
RUN chmod -R +r /data

WORKDIR /code
ADD requirements.txt /code
ADD requirements.dev.txt /code
ADD .docker/install_dev_requirements.sh /code

RUN pip3 install -r requirements.txt
RUN chmod +x install_dev_requirements.sh && ./install_dev_requirements.sh

ADD ./ /code
