FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-8-amq-broker-80-openshift-rhel8@sha256:a1178be6722e6e324c00130b12f8b119966ce8ce5c706284c471067001a48ca3

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

USER 185

LABEL name="amq-broker-7/amq-broker-7x-init-rhel8"
LABEL description="Red Hat AMQ 7.x.x Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.x.x"
LABEL summary="Red Hat AMQ 7.x.x Init"
LABEL amq.broker.version="7.x.x.CON.1.CR1"
LABEL com.redhat.component="amq-broker-init-rhel8-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.x.x Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
