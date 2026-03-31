# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY murder_wizard_web/frontend/package*.json ./
RUN npm ci

COPY murder_wizard_web/frontend/ ./
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY murder_wizard_web/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
