FROM node:alpine AS builder

WORKDIR /app

COPY ./common ./common
COPY ./bot/ ./bot
COPY ./package*.json ./
COPY ./tsconfig*.json ./

RUN npm ci --omit=dev
RUN npm run build

CMD ["npm", "run", "bot"]
