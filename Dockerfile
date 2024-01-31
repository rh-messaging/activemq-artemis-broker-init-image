FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-7-amq-broker-711-openshift-rhel8@sha256:e8fa2a00e576ecb95561ffbdbf87b1c82d479c8791ab2c6ce741dd0d0b496d15

USER root

ADD script /opt/amq-broker/script

### BEGIN REMOTE SOURCE
ARG REMOTE_SOURCE_DIR=/tmp/remote_source
ARG REMOTE_SOURCE_REF=418c4b84997836f02f4ce32ec413efc79374e6c2
ARG REMOTE_SOURCE_REP=https://github.com/artemiscloud/yacfg.git
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

LABEL name="amq-broker-7/amq-broker-711-init-rhel8"
LABEL description="Red Hat AMQ 7.11.6 Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.11.6"
LABEL summary="Red Hat AMQ 7.11.6 Init"
LABEL amq.broker.version="7.11.6.CON.1.CR2"
LABEL com.redhat.component="amq-broker-init-rhel8-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.11.6 Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
