FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-7-amq-broker-712-openshift-rhel8@sha256:0360692becdf857a1546c88f3a2026cfc16459c043e4b5efe4a3854a10fe992c

USER root

ADD script /opt/amq-broker/script

ARG REMOTE_SOURCE_REF=0467611bb875f50fdee76431dfb9d34dc79b8a7f
ARG REMOTE_SOURCE_REP=https://github.com/artemiscloud/yacfg.git
ENV REMOTE_SOURCE_URL=$REMOTE_SOURCE_REP#$REMOTE_SOURCE_REF
### BEGIN REMOTE SOURCE
ARG REMOTE_SOURCE_DIR=/tmp/remote_source
RUN microdnf install -y git && microdnf clean all && rm -rf /var/cache/yum
RUN mkdir -p $REMOTE_SOURCE_DIR/app
RUN git clone $REMOTE_SOURCE_REP $REMOTE_SOURCE_DIR/app
RUN cd $REMOTE_SOURCE_DIR/app && git checkout $REMOTE_SOURCE_REF
### END REMOTE SOURCE
WORKDIR $REMOTE_SOURCE_DIR/app

RUN chmod g+rwx $REMOTE_SOURCE_DIR/app

RUN microdnf install -y python38 python38-jinja2 python38-pyyaml && \
    microdnf clean all && rm -rf /var/cache/yum

RUN python3 setup.py install

LABEL name="amq-broker-7/amq-broker-712-init-rhel8"
LABEL description="Red Hat AMQ 7.12.0 Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.12.0"
LABEL summary="Red Hat AMQ 7.12.0 Init"
LABEL amq.broker.version="7.12.0.CON.1.SR1"
LABEL com.redhat.component="amq-broker-init-rhel8-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.12.0 Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
