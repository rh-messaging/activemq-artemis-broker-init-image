FROM registry-proxy.engineering.redhat.com/rh-osbs/amq-broker-7-amq-broker-711-openshift-rhel8@sha256:137b893ad15e0cd5353bae134c8fae833257a12641b12d0f774f1565ce66f63c

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
LABEL description="Red Hat AMQ 7.11.7 Init"
LABEL maintainer="Howard Gao <hgao@redhat.com>"
LABEL version="7.11.7"
LABEL summary="Red Hat AMQ 7.11.7 Init"
LABEL amq.broker.version="7.11.7.CON.1.CR2"
LABEL com.redhat.component="amq-broker-init-rhel8-container"
LABEL io.k8s.display-name="Red Hat AMQ 7.11.7 Init"
LABEL io.openshift.tags="messaging,amq,java,jboss,xpaas,init"
