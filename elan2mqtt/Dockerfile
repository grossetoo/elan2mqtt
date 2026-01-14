ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-virtualenv \
    build-base

# Create app directory
WORKDIR /elan2mqtt-2.0.0

# Copy requirements and install Python packages
COPY requirements.txt .
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt

# Copy Python script
COPY main_worker.py .

# Copy run script
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
