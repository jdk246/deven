
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies and build
# Copy package manifests first for better layer caching
COPY package.json package-lock.json* /app/
RUN npm ci --production=false --silent

# Copy source files
COPY . /app

# Ensure the API base is available at build; Railway will inject VITE_API_BASE_URL in the build environment
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# Production image
FROM node:20-alpine AS runtime
WORKDIR /app

# Install a tiny static serve utility (serve) globally
RUN npm install -g serve

# Copy built assets
COPY --from=build /app/dist /app/dist

ENV PORT=5173

EXPOSE 5173
# serve on $PORT
CMD ["sh", "-c", "serve -s /app/dist -l ${PORT:-5173}"]