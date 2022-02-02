FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-7-amq-broker-710-openshift-rhel8@sha256:24cf7ccffb717185f347def50ad3e6782dc196f680a1d3ba1b4ca7c06ca66a6d

USER root

ADD script /opt/amq-broker/script

### BEGIN REMOTE SOURCE
ARG REMOTE_SOURCE_DIR=/tmp/remote_source
ARG REMOTE_SOURCE_REF=4f381a9554dd59c7fa3e99858f99daec2220aefe
ARG REMOTE_SOURCE_REP=https://github.com/rh-messaging-qe/yacfg.git
RUN yum install -y git && yum clean all && rm -rf /var/cache/yum
RUN mkdir -p $REMOTE_SOURCE_DIR/app
RUN git clone $REMOTE_SOURCE_REP $REMOTE_SOURCE_DIR/app
RUN cd $REMOTE_SOURCE_DIR/app && git checkout $REMOTE_SOURCE_REF
### END REMOTE SOURCE
WORKDIR $REMOTE_SOURCE_DIR/app

RUN chmod g+rwx $REMOTE_SOURCE_DIR/app

RUN yum install -y python38 python38-jinja2 python38-pyyaml && \
    yum clean all && rm -rf /var/cache/yum

RUN python3 setup.py install

LABEL name="amq-broker-7/amq-broker-710-init-rhel8"
LABEL summary="Red Hat AMQ 7.10.0 Init"
LABEL description="Red Hat AMQ 7.10.0 Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.10"
LABEL amq.broker.version="7.10.0.ER1"
LABEL io.k8s.display-name="Red Hat AMQ 7.10.0 Init"
LABEL com.redhat.component="amq-broker-init-rhel8-container"
