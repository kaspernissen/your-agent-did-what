# The console as a container: five static files and an nginx config.
#
# No build step and no framework on purpose. The page is one HTML file with inline CSS and
# JavaScript, so it can be read end to end by someone who wants to see what the demo is
# actually asking each agent — which is most of why it exists.
FROM nginx:1.27-alpine

# Into templates/ rather than conf.d/: the entrypoint runs envsubst over this directory and
# writes the result to conf.d, which is how the resolver line gets the cluster's DNS.
COPY default.conf.template /etc/nginx/templates/default.conf.template

# Fills NGINX_LOCAL_RESOLVERS from /etc/resolv.conf before nginx starts.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1

# Substitute that one variable and nothing else. Without the filter, envsubst replaces every
# environment variable it finds — and a pod's environment includes the auto-injected
# KUBERNETES_* and HOSTNAME, so an unlucky config could be rewritten out from under itself.
ENV NGINX_ENVSUBST_FILTER=^NGINX_LOCAL_RESOLVERS$

COPY index.html markdown.js capybara.png beaver.png otter.png /usr/share/nginx/html/

EXPOSE 80
