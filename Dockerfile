FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-8-amq-broker-80-openshift-rhel9@sha256:1e99216ef103642028c80d982ce2964f402da7524bf810da8a7c05d2e2f0bd59

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

LABEL name="amq-broker-8/amq-broker-80-init-rhel9"
LABEL description="Red Hat AMQ 8.0.0 Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="8.0.0"
LABEL summary="Red Hat AMQ 8.0.0 Init"
LABEL amq.broker.version="8.0.0.CON.1.SR1"
LABEL com.redhat.component="amq-broker-init-rhel9-container"
LABEL io.k8s.display-name="Red Hat AMQ 8.0.0 Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
