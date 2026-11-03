FROM node:20-bookworm AS build

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-pip nginx ca-certificates curl gnupg && mkdir -p --mode=0755 /usr/share/keyrings && curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg && printf '%s\n' 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' > /etc/apt/sources.list.d/cloudflared.list && apt-get update && apt-get install -y --no-install-recommends cloudflared && rm -rf /var/lib/apt/lists/*

COPY frontend/package*.json frontend/
RUN cd frontend && npm install --no-audit --no-fund
COPY frontend/ frontend/
ARG NEXT_PUBLIC_API_URL=/api
ARG NEXT_PUBLIC_APP_NAME=CRM Sofia
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_APP_NAME=$NEXT_PUBLIC_APP_NAME
RUN cd frontend && npm run typecheck && npm run build

COPY backend/ backend/
RUN python3 -m pip install --break-system-packages ./backend

COPY deploy/sofia/nginx.conf /etc/nginx/nginx.conf
COPY deploy/sofia/start.sh /usr/local/bin/sofia-start
RUN chmod +x /usr/local/bin/sofia-start && mkdir -p /app/data /run/nginx

EXPOSE 8080
CMD ["/usr/local/bin/sofia-start"]
