ARG TAG
FROM mindsync/e2e-test-base:${TAG}

ENV HOME /home/chrome

COPY requirements.txt .
# RUN /install-requirements.sh
RUN pip install -U pip && pip install -r requirements.txt && pip freeze

ADD 3fdkgzzo.default-esr.tar.gz "${HOME}/.mozilla/firefox/"

RUN chown -R chrome:chrome "${HOME}/.mozilla/firefox" && \
    mkdir "${HOME}/e2e-tests" && \
    chown -R chrome:chrome "${HOME}/e2e-tests"

RUN curl -fsSL https://deb.nodesource.com/setup_14.x | bash -

RUN apt update && \
    apt install -y git nodejs postgresql-client

RUN sed -i 's/#\s\+StrictHostKeyChecking ask/   StrictHostKeyChecking no/g' /etc/ssh/ssh_config

USER chrome

RUN mkdir "${HOME}/Downloads"

WORKDIR "${HOME}/e2e-tests"

RUN mkdir /tmp/failure_logs /tmp/logs

ENTRYPOINT ["/home/chrome/e2e-tests/run.sh"]

COPY --chown=chrome:chrome ssh-key/id_rsa "${HOME}/.ssh/id_rsa"
RUN chmod 600 "${HOME}/.ssh/id_rsa"

ENV DB_SQL_CLIENT=postgres \
    DB_SQL_HOST=db.example.com \
    DB_SQL_PORT=5432 \
    DB_SQL_USERNAME=db_username \
    DB_SQL_PASSWORD=db_password \
    DB_SQL_DATABASE=db_name \
    DB_SQL_POOL_MIN=0 \
    DB_SQL_POOL_MAX=40 \
    DB_SQL_USERNAME_MIGRATE=db_username \
    DB_SQL_PASSWORD_MIGRATE=db_password \
    BACKEND_API_DIR="${HOME}/psql-migrations-repo"

ARG SKIP_DB_WIPE
ARG CACHE_BUST=1

# Repository with psql migrations. Uncomment if migrations should be applied

# RUN test -z "${SKIP_DB_WIPE}" && \
#     cd "${HOME}" && \
#     git clone git@bitbucket.org:some-org/psql-migrations-repo.git && \
#     cd "${BACKEND_API_DIR}" && \
#     git checkout master && \
#     npm install || true

COPY --chown=chrome:chrome *.py *.ini *.sh ./
