FROM python:3.10-slim

# Install base dependencies and John the Ripper
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    libldap2-dev \
    libsasl2-dev \
    libkrb5-dev \
    wget \
    unzip \
    john \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt

# Clone ADenum
RUN git clone https://github.com/SecuProject/ADenum.git

# Install Python dependencies
WORKDIR /opt/ADenum
RUN pip install --no-cache-dir -r requirements.txt

# Install Impacket
WORKDIR /opt
RUN git clone https://github.com/fortra/impacket.git
WORKDIR /opt/impacket
RUN pip install .

# Symlink Impacket example scripts (force overwrite if needed)
RUN ln -sf /opt/impacket/examples/* /usr/local/bin/

# Download rockyou.txt wordlist
RUN mkdir -p /opt/wordlists && \
    wget https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt \
         -O /opt/wordlists/rockyou.txt && \
    chmod 644 /opt/wordlists/rockyou.txt

# Set final working directory
WORKDIR /opt/ADenum

# Default entrypoint
ENTRYPOINT ["python3", "ADenum.py"]