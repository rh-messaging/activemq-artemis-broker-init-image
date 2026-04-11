FROM quay.io/arkmq-org/arkmq-org-broker-kubernetes@sha256:6855d008e0a11b5110395ac321daaf69cfde24e36188c50e2b0291069e5a6234

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

# The user is in the group 0 to have access to the volumes mounted
# by Kubernetes that are typically owned by UID 0 (root) and GID 0 (root).
USER 185:0

LABEL name="amq-broker-7/amq-broker-7x-init-rhel9"
LABEL description="Red Hat AMQ 7.x.x Init"
LABEL maintainer="Red Hat, Inc."
LABEL version="7.x.x"
LABEL org.opencontainers.image.title="Red Hat AMQ Broker OpenShift container image"
LABEL org.opencontainers.image.description="Red Hat AMQ Broker Init container image for configuring AMQ Broker in containerized environments"
LABEL org.opencontainers.image.vendor="Red Hat, Inc."
LABEL summary="Red Hat AMQ 7.x.x Init"
LABEL amq.broker.version="7.x.x.CON.1.CR1"
LABEL com.redhat.component="amq-broker-init-rhel9-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.x.x Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
