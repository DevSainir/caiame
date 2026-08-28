FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# The image substitutes ${DOMAIN} into templates at start-up. The filter is what keeps it
# from also eating nginx's own $host, $uri and $remote_addr.
ENV NGINX_ENVSUBST_FILTER=DOMAIN
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
