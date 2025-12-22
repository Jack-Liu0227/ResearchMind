# ============================================
# Stage 1: Build stage
# ============================================
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including devDependencies for build)
# Use npm install instead of npm ci to handle package.json changes
RUN npm install

# Copy source code
COPY . .

# Build the application (with relaxed type checking for Docker builds)
RUN npm run build:docker

# ============================================
# Stage 2: Production stage with Nginx
# ============================================
FROM nginx:alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create a simple health check endpoint
RUN echo '<!DOCTYPE html><html><body>OK</body></html>' > /usr/share/nginx/html/health.html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/health.html || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]