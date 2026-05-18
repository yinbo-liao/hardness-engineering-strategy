FROM node:22-alpine

RUN addgroup -S harness && adduser -S harness -G harness

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --legacy-peer-deps

COPY . .

RUN chown -R harness:harness /app
USER harness

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
