# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Production runtime
FROM node:20-alpine

WORKDIR /app

# Copy built application
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --production

# Expose port
EXPOSE 3000

# Set environment to production
ENV NODE_ENV=production

ENV NODE_OPTIONS="--max-old-space-size=4096"

# Start the application
CMD ["node", "build"]
