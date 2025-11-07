# start by pulling the python image
FROM --platform=linux/amd64 python:3.13
# Установка временной зоны и сертификатов
RUN apt-get update && apt-get install -y \
    ca-certificates \
    tzdata \
    && ln -sf /usr/share/zoneinfo/UTC /etc/localtime \
    && echo "UTC" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

#FROM python
# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt
# switch working directory
WORKDIR /app
# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt
RUN pip install python-netbox
# copy every content from the local file to the image
COPY . /app
# create storage dir for mounting
RUN mkdir -p /srv/storage

# nicegui storage change
#ENV NICEGUI_STORAGE_PATH=/srv/storage/nicegui_storage
RUN mkdir -p /app/teleport
WORKDIR /app/teleport
#install teleport tsh 12
RUN curl -O https://cdn.teleport.dev/teleport-v12.4.9-linux-amd64-bin.tar.gz
RUN tar -xzf /app/teleport/teleport-v12.4.9-linux-amd64-bin.tar.gz
RUN mv teleport teleport_12
RUN rm /app/teleport/teleport-v12.4.9-linux-amd64-bin.tar.gz

#install teleport tsh 17
RUN curl -O https://cdn.teleport.dev/teleport-v17.7.7-linux-amd64-bin.tar.gz
RUN tar -xzf /app/teleport/teleport-v17.7.7-linux-amd64-bin.tar.gz
RUN mv teleport teleport_17
RUN rm /app/teleport/teleport-v17.7.7-linux-amd64-bin.tar.gz

# configure the container to run in an executed manner
WORKDIR /app
ENTRYPOINT ["python"]
#CMD ["front.py"]

#build command
#sudo docker image build -t universal_harvester_docker_amd64 .

# экспорт
# docker save universal_harvester_docker_amd64 -o universal_harvester_docker_amd64.tar
# перенос через upload
# импорт
#root@:~# docker load < universal_harvester_docker_amd64.tar