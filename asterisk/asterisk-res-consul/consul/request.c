#include <stdlib.h>
#include <string.h>

#include "consul.h"

static const char *http_method[] = {
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "HEAD",

    "OPTION"
};

CURLU* consul_url_create(int version, enum CONSUL_API_TYPE type, const char *path) {
    CURLU *url;
    CURLMcode rc;
    char url_path[PATH_MAX];
    const char *prefix;

    switch (type) {
    case CONSUL_KEYS: prefix = "kv"; break;
    case CONSUL_SERVICES: prefix = "health/service"; break;
    case CONSUL_AGENT_REGISTER: prefix = "agent/service/register"; break;
    case CONSUL_AGENT_DEREGISTER: prefix = "agent/service/deregister"; break;
    case CONSUL_AGENT_SET_MAINTENANCE: prefix = "agent/service/maintenance"; break;
    }

    url = curl_url();
    if (path && path[0] != '\0') {
        snprintf(url_path, PATH_MAX, "/v%d/%s/%s", version, prefix, path);
    } else {
        snprintf(url_path, PATH_MAX, "/v%d/%s", version, prefix);
    }
    if ((rc = curl_url_set(url, CURLUPART_PATH , url_path, 0)) != CURLM_OK) {
        curl_url_cleanup(url);
        return NULL;
    };

    return url;
}

size_t consul_header_callback(char *buffer, size_t size,
                              size_t nitems, void *userdata)
{
    int status_code;
    char *sep;
    char *saveptr;
    char* key;
    char *value;
    char *suffix;
    consul_response_t* resp;

    int count = nitems * size;

    resp = (consul_response_t*) userdata;

    if (!resp->err) {
        resp->err = (consul_error_t*) calloc(1, sizeof(consul_error_t));

        buffer = strtok_r(buffer, "\r\n", &saveptr);
        if (!buffer) {
            resp->err->ecode = ERROR_INVALID_RESPONSE;
            return 0;
        }

        const char* http_version = "HTTP/1.1 ";
        size_t http_size = strlen(http_version);
        if (strncmp(buffer, http_version, http_size)) {
            resp->err->ecode = ERROR_INVALID_RESPONSE;
            return 0;
        }

        buffer += http_size;

        if (sscanf(buffer, "%3d", &status_code) != 1) {
            resp->err->ecode = ERROR_INVALID_RESPONSE;
            return 0;
        }

        buffer += 3;
        if (buffer[0] != '\0') {
            resp->err->message = strdup(buffer+1);
        }

        resp->err->ecode = status_code;
    } else {
        if ((sep = index(buffer, ':'))) {
            *sep = '\0';
            key = buffer;
            buffer = sep + 1;
            while (*buffer != '\0' && *buffer == ' ') buffer++;
            if ((suffix = strstr(buffer, "\r\n"))) {
                *suffix = '\0';
                value = buffer;
                if (!(strcmp(key, "X-Consul-Index"))) {
                    resp->modify_index = atoi(value);
                } else if (!strcmp(key, "Transfer-Encoding") && !strcmp(value, "chunked")) {
                    resp->chunked = 1;
                }
            }
        }
    }

    return count;
}

size_t consul_body_callback(void *contents, size_t length, size_t nmemb, void *userp) {
    consul_response_t* resp = (consul_response_t*) userp;
    size_t size = length * nmemb;
    if (resp->data && resp->chunked) {
        size_t previous_size = resp->data_length;
        resp->data_length += size;
        resp->data = realloc(resp->data, resp->data_length);
        strncpy(resp->data+previous_size, (const char*) contents, size);
    }
    else {
        resp->data = malloc(size);
        strncpy(resp->data, contents, size);
        resp->data_length = size;
    }
    return size;
}

int consul_response_is_success(consul_response_t *response) {
    return response->err && (response->err->ecode >= 200) && (response->err->ecode < 300);
}

consul_response_t* consul_response_create() {
    return (consul_response_t*) calloc(1, sizeof(consul_response_t));
}

void consul_request_setopt(consul_request_t* req, consul_response_t* resp, CURL *curl) {
    curl_easy_reset(curl);

    curl_easy_setopt(curl, CURLOPT_CURLU, req->url);
    curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, http_method[req->method]);
    if (req->client->settings.user) {
        curl_easy_setopt(curl, CURLOPT_USERNAME, req->client->settings.user);
    }
    if (req->client->settings.password) {
        curl_easy_setopt(curl, CURLOPT_PASSWORD, req->client->settings.password);
    }

    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);

    curl_easy_setopt(curl, CURLOPT_HEADERFUNCTION, consul_header_callback);
    curl_easy_setopt(curl, CURLOPT_HEADERDATA, resp);

    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, consul_body_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, resp);

    if (req->data) {
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, req->data);
    }

    #if LIBCURL_VERSION_NUM >= 0x071900
    curl_easy_setopt(curl, CURLOPT_TCP_KEEPALIVE, 1L);
    curl_easy_setopt(curl, CURLOPT_TCP_KEEPINTVL, 1L); /*the same as go-etcd*/
    #endif
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "consul-client");
    curl_easy_setopt(curl, CURLOPT_POSTREDIR, 3L);     /*post after redirecting*/

    curl_easy_setopt(curl, CURLOPT_VERBOSE, req->client->settings.verbose);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, req->client->settings.connect_timeout);
}

consul_response_t* consul_request_send(consul_request_t* req) {
    CURLMcode rc;
    consul_response_t* resp = NULL;

    resp = (consul_response_t*) calloc(1, sizeof(consul_response_t));

    consul_request_setopt(req, resp, req->curl);

    rc = curl_easy_perform(req->curl);

    if (rc != CURLM_OK) {
        if (resp->err == NULL) {
            resp->err = (consul_error_t*) calloc(1, sizeof(consul_error_t));
            resp->err->ecode = ERROR_REQUEST_FAILED;
            resp->err->message = strdup(curl_easy_strerror(rc));
        }
    }

    return resp;
}

void consul_response_reset(consul_response_t* response) {
    if (response->err) {
        if (response->err->message) {
            free(response->err->message);
        }
        free(response->err);
        response->err = NULL;
    }

    if (response->value) {
        free(response->value);
        response->value = NULL;
    }

    if (response->key) {
        free(response->key);
        response->key = NULL;
    }

    if (response->keys) {
        for (int i = 0; i < response->key_count; i++) {
            free(response->keys[i]);
        }
        free(response->keys);
        response->key_count = 0;
        response->keys = NULL;
    }

    if (response->data) {
        free(response->data);
        response->data = NULL;
    }

    memset(response, 0, sizeof(consul_response_t));
}

void consul_response_cleanup(consul_response_t* response) {
    consul_response_reset(response);
    free(response);
}

consul_request_t* consul_client_request_create(consul_client_t* client, enum HTTP_METHOD method, CURLU* url, const char *data) {
    consul_request_t* req = (consul_request_t*) calloc(1, sizeof(consul_request_t));
    req->curl = curl_easy_init();
    req->method = method;
    req->url = url;
    req->client = client;
    req->data = data;
    return req;
}

int consul_response_parse(consul_response_t *response, consul_response_parser parser) {
    json_t* root;
    json_error_t err;

    if (response->data) {
        root = json_loadb(response->data, response->data_length, JSON_DECODE_ANY, &err);
        if (!root) {
            printf("failed to load json (%s), %s, line %d, column %d, position %d!\n", response->data, err.text, err.line, err.column, err.position);
            return -1;
        }
        return parser(response, root);
    }

    return -1;
}

void consul_request_set_server(consul_request_t* request, consul_server_t* server) {
    curl_url_set(request->url, CURLUPART_SCHEME, server->scheme, 0);
    curl_url_set(request->url, CURLUPART_HOST, server->host, 0);
    curl_url_set(request->url, CURLUPART_PORT, server->port, 0);
}

void consul_request_cleanup(consul_request_t* request) {
    curl_easy_cleanup(request->curl);
    if (request->data)
        free((void*) request->data);
}

consul_response_t* consul_cluster_request(consul_client_t* client, consul_request_t* req) {
    consul_response_t* resp;
    int i;

    for (i = 0; i < client->server_count; i++) {
        consul_request_set_server(req, client->servers[client->leader]);

        resp = consul_request_send(req);

        if (!resp || !resp->err || resp->err->ecode == ERROR_REQUEST_FAILED) {
            client->leader = (client->leader + 1) % client->server_count;
            continue;
        } else {
            break;
        }
    }

    return resp;
}