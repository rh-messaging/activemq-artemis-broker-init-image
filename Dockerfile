FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-7-amq-broker-714-openshift-rhel9@sha256:3243a74fd90299528386ee12d1ac0094294872ad1b55ee4f90144ae2f8459f44

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

LABEL name="amq-broker-7/amq-broker-714-init-rhel9"
LABEL description="Red Hat AMQ 7.14.2 Init"
LABEL maintainer="Red Hat, Inc."
LABEL version="7.14.2"
LABEL summary="Red Hat AMQ 7.14.2 Init"
LABEL amq.broker.version="7.14.2.CON.1.SR1"
LABEL com.redhat.component="amq-broker-init-rhel9-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.14.2 Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
