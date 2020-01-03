#include <stdlib.h>

#include "consul.h"

consul_server_t* consul_server_create(const char *url) {
    consul_server_t *server;
    CURLU* curlu;
    CURLMcode rc;

    server = (consul_server_t*) calloc(1, sizeof(consul_server_t));
    if (server) {
        curlu = curl_url();

        if ((rc = curl_url_set(curlu, CURLUPART_URL, url, 0)) != CURLM_OK) {
            return NULL;
        }

        curl_url_get(curlu, CURLUPART_SCHEME, &server->scheme, 0);
        curl_url_get(curlu, CURLUPART_HOST, &server->host, 0);
        curl_url_get(curlu, CURLUPART_PORT, &server->port, 0);

        curl_url_cleanup(curlu);
    }

    return server;
}

void consul_server_cleanup(consul_server_t* server) {
    if (server->host)
        curl_free(server->host);
    if (server->port)
        curl_free(server->port);
    if (server->scheme)
        curl_free(server->scheme);
}