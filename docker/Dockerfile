# https://docs.astral.sh/uv/guides/integration/docker/#python-slim-images
FROM ghcr.io/astral-sh/uv:python3.12-bookworm
#ARG CACHEBUST=2025-07-15-14-16-18

# Needed to properly handle UTF-8
ENV PYTHONIOENCODING=UTF-8
ENV LANG=en_US.UTF-8

WORKDIR /

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    util-linux \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# NOTE all the crap below is needed to make pygraphviz work, but we probably don't need to include this
# in the new grader image? We can add back if necessary but not sure what the use cases are.
#    dos2unix \
#    graphviz \
#    graphviz-devel

COPY requirements.txt /
ARG PACKAGE_VERSION=latest
RUN uv venv --seed && uv pip install --no-cache-dir -r requirements.txt --prefer-binary && \
    uv pip install --no-cache-dir pytest-prairielearn-grader==${PACKAGE_VERSION} --prefer-binary

# Anything that needs to be run post-install
# TODO Not clear yet how to make the grader run subprocess as a less privileged user
# RUN useradd ag
COPY --chmod=755 run.sh /run.sh

# Add serverFilesCourse to Python path
# TODO do we need to copy anything here?
ENV PYTHONPATH=/grade/serverFilesCourse/

ENTRYPOINT [ "/run.sh" ]
