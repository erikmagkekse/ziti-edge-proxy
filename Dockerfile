FROM python:3-slim-bookworm

# Arguments
ENV USER=appuser
ENV GROUP=$USER
ENV UID=12345
ENV GID=23456
ENV USER_HOME=/app
ENV VIRTUAL_ENV=$USER_HOME/.venv

ENV SOCKS_ENABLED=TRUE
ENV HTTP_ENABLED=TRUE

ENV PROXY_HOST=127.0.0.1
ENV SOCKS_PORT=1080
ENV HTTP_PORT=1080
ENV PROXY_USERNAME=user
ENV PROXY_PASSWORD=password

# Go to app dir
RUN mkdir /app
WORKDIR /app

# Create User and group
RUN addgroup \
    --gid "$GID" \
    "$GROUP" \
&&  adduser \
    --disabled-password \
    --gecos "" \
    --home $USER_HOME \
    --ingroup "$GROUP" \
    --no-create-home \
    --uid "$UID" \
    $USER

# Chown permissions of user dir
RUN chown -R $USER:$GROUP /app


# Switch to user
USER $USER

# Copy files over and adjust perms
COPY --chown=$USER:$GROUP src/main.py /app/main.py
COPY --chown=$USER:$GROUP requirements.txt /app/requirements.txt
COPY --chown=$USER:$GROUP entrypoint.sh /app/entrypoint.sh
RUN chmod 755 /app/entrypoint.sh

# Setup Python venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Ansible
RUN pip3 install --no-cache -r requirements.txt

# Start Python script, entrypoint and configure port
EXPOSE 1080
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
CMD [ "python", "main.py" ]
