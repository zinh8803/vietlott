# Stage 1: Build React App
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve using Nginx
FROM nginx:stable-alpine

# Copy file cấu hình Nginx riêng cho React Router & proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy thư mục đã build
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
