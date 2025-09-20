# Multi-stage build for production optimization
# Stage 1: Build the application
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json ./

# Install dependencies with specific flags for production build
RUN npm ci --only=production=false --frozen-lockfile

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Production server with Node.js serve
FROM node:20-alpine AS production

# Install system dependencies in one layer
RUN apk add --no-cache \
    dumb-init \
    curl \
    && npm install -g serve@14 \
    && npm cache clean --force

# Create app user for security with proper naming
RUN addgroup -g 1001 -S appgroup && \
    adduser -S -D -H -u 1001 -h /app -s /sbin/nologin -G appgroup -g appgroup appuser

# Set working directory
WORKDIR /app

# Copy built application from builder stage with proper ownership
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist

# Switch to non-root user early
USER appuser

# Expose port
EXPOSE 3000

# Add labels for better metadata
LABEL maintainer="Clotho Team" \
      version="1.0" \
      description="Clotho - AI-powered supply chain optimizer"

# Health check with curl instead of wget (more reliable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:3000/ || exit 1

# Use dumb-init as entrypoint for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Start the application with serve and production optimizations
CMD ["serve", "-s", "dist", "-l", "3000", "--no-clipboard", "--no-compression"]