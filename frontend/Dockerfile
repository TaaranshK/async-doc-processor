# ==============================================================================
# Frontend — Vite + React Application
# ==============================================================================
FROM node:20-alpine as base

WORKDIR /app

# ==============================================================================
# Build Stage
# ==============================================================================
FROM base as build

COPY package.json package-lock.json* ./

# Install dependencies (use install instead of ci for more flexibility)
RUN npm install --omit=dev 2>&1 || npm install

# Copy source code
COPY . .

# Build application
RUN npm run build

# ==============================================================================
# Production Stage
# ==============================================================================
FROM base as production

# Install serve to run the production build
RUN npm install -g serve

# Copy built application from build stage
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

CMD ["serve", "-s", "dist", "-l", "3000"]

# ==============================================================================
# Development Stage
# ==============================================================================
FROM base as development

COPY package.json package-lock.json* ./

# Install dependencies (use install instead of ci for more flexibility)
RUN npm install

# Copy source code
COPY . .

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:5173 || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
