FROM ubuntu:14.04
ENV DEBIAN_FRONTEND noninteractive
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y build-essential
RUN apt-get install -y python-pip python-dev libmysqld-dev liblzma-dev zlib1g-dev git libffi-dev libssl-dev cmake
RUN apt-get install -y wget
RUN pip install pip --upgrade
RUN wget https://github.com/libgit2/libgit2/archive/v0.22.0.tar.gz && \
    tar xzf v0.22.0.tar.gz && \
    cd libgit2-0.22.0/ && \
    cmake . && \
    make && make install
ADD eru-core /opt/eru-core
WORKDIR /opt/eru-core
RUN export LDFLAGS="-Wl,-rpath='/usr/local/lib',--enable-new-dtags $LDFLAGS" && pip install -r ./requirements.txt && python setup.py install
