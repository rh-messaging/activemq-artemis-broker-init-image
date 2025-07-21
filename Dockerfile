FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-7-amq-broker-713-openshift-rhel9@sha256:e58d2f652106ccd55d1816acc64efe8905e8737f4d4b5fabca5232aeb3de73a7

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

LABEL name="amq-broker-7/amq-broker-713-init-rhel9"
LABEL description="Red Hat AMQ 7.13.1 Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.13.1"
LABEL summary="Red Hat AMQ 7.13.1 Init"
LABEL amq.broker.version="7.13.1.CON.1.SR1"
LABEL com.redhat.component="amq-broker-init-rhel9-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.13.1 Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
