FROM quay.io/arkmq-org/activemq-artemis-broker-kubernetes@sha256:673384959d87408cab9fc92f305dc47b3e7bad3a81b182de104d47f76e7df4e1

USER root

ADD script /opt/amq-broker/script

ARG REMOTE_SOURCE_REF=0467611bb875f50fdee76431dfb9d34dc79b8a7f
ARG REMOTE_SOURCE_REP=https://github.com/arkmq-org/yacfg.git
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

RUN microdnf install -y python3 python3-jinja2 python3-pyyaml && \
    microdnf clean all && rm -rf /var/cache/yum

RUN python3 setup.py install

USER 185

LABEL name="amq-broker-7/amq-broker-7x-init-rhel9"
LABEL description="Red Hat AMQ 7.x.x Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.x.x"
LABEL summary="Red Hat AMQ 7.x.x Init"
LABEL amq.broker.version="7.x.x.CON.1.CR1"
LABEL com.redhat.component="amq-broker-init-rhel9-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.x.x Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
