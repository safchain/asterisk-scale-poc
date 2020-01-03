#include <stdlib.h>
#include <string.h>

#include <jansson.h>

#include "consul.h"
#include "base64.h"

consul_client_t* consul_client_create(int server_count, const char** servers) {
    int i;
    consul_client_t* client = (consul_client_t*) calloc(1, sizeof(consul_client_t));

    if (server_count < 1)
        return NULL;

    client->server_count = server_count;
    client->servers = (consul_server_t**) calloc(server_count, sizeof(consul_server_t*));
    client->settings.connect_timeout = 5000;
    if (!client->servers)
        return NULL;

    for (i = 0; i < server_count; i++) {
        if ((client->servers[i] = consul_server_create(servers[i])) == NULL) {
            return NULL;
        }
    }

    return client;
}

void consul_client_setup_user(consul_client_t* client, const char *user, const char *password) {
    client->settings.user = strdup(user);
}

void consul_client_destroy(consul_client_t* client) {
    int i = 0;

    if (client->settings.user) {
        free(client->settings.user);
    }

    for (i = 0; i < client->server_count; i++) {
        consul_server_cleanup(client->servers[i]);
    }

    free(client->servers);
}

int consul_parse_lsdir_response(consul_response_t* response, json_t* root) {
    json_t *jstr;
    int count = json_array_size(root);

    response->key_count = count;
    response->keys = calloc(count, sizeof(char*));

    for (int i = 0; i < count; i++){
        jstr = json_array_get(root, i);
        if (jstr == NULL || !json_is_string(jstr)) continue;
        response->keys[i] = (char*) json_string_value(jstr);
    }

    return 0;
}

static int consul_parse_success(consul_response_t* response, json_t* root) {
    json_unpack(root, "b", &response->success);
    return 0;
}

static char *consul_ensure_folder(const char *key) {
    char *folder = strdup(key);
    int size = strlen(key);
    if (!size) {
        return NULL;
    }

    if (folder[size-1] != '/') {
        strcat(folder, "/");
    }

    return folder;
}

int consul_parse_get_response(consul_response_t* response, json_t* root) {
    json_unpack(root, "[{s:i, s:s, s:i, s:s, s:i, s:i}]", "LockIndex", &response->lock_index,
        "Key", &response->key, "Flags", &response->flags, "Value", &response->value,
        "CreateIndex", &response->create_index, "ModifyIndex", &response->modify_index);

    unsigned char *decoded;
    long unsigned decoded_size;

    if (response->value) {
        decoded = base64_decode((const unsigned char*) response->value, strlen(response->value), &decoded_size);

        if (decoded_size) {
            response->value = (char*) decoded;
        }
    }

    return 0;
}

consul_request_t* consul_client_request_create_get(consul_client_t *client, const char *key, int recursive, int keys) {
    CURLU *url = consul_url_create(CONSUL_API_VERSION, CONSUL_KEYS, key);

    if (keys) {
        curl_url_set(url, CURLUPART_QUERY, "keys=true", CURLU_APPENDQUERY);
        curl_url_set(url, CURLUPART_QUERY, "separator=%2F", CURLU_APPENDQUERY);
    }

    if (recursive) {
        curl_url_set(url, CURLUPART_QUERY, "recurse=true", CURLU_APPENDQUERY);
    }

    return consul_client_request_create(client, CONSUL_HTTP_GET, url, NULL);
}

consul_response_t *consul_client_get(consul_client_t *client, const char *key, int recursive, int keys) {
    consul_request_t *req;
    consul_response_t *resp;

    req = consul_client_request_create_get(client, key, recursive, keys);
    resp = consul_cluster_request(client, req);
    if (resp) {
        if (keys) {
            consul_response_parse(resp, consul_parse_get_response);
        } else {
            consul_response_parse(resp, consul_parse_lsdir_response);
        }
    }
    consul_request_cleanup(req);
    return resp;
}

consul_response_t *consul_client_lsdir(consul_client_t *client, const char *key, int recursive) {
    return consul_client_get(client, key, recursive, 1);
}


consul_response_t *consul_client_put(consul_client_t *client, const char *key, char *value) {
    consul_request_t *req;
    consul_response_t *resp;
    CURLU *url;

    url = consul_url_create(CONSUL_API_VERSION, CONSUL_KEYS, key);
    req = consul_client_request_create(client, CONSUL_HTTP_PUT, url, value);
    resp = consul_cluster_request(client, req);
    if (resp) {
        consul_response_parse(resp, consul_parse_success);
    }

    curl_url_cleanup(url);
    return resp;
}

consul_response_t *consul_client_delete(consul_client_t *client, const char *key) {
    consul_request_t *req;
    consul_response_t *resp;
    CURLU *url;

    url = consul_url_create(CONSUL_API_VERSION, CONSUL_KEYS, key);
    req = consul_client_request_create(client, CONSUL_HTTP_DELETE, url, NULL);
    resp = consul_cluster_request(client, req);
    if (resp) {
        consul_response_parse(resp, consul_parse_success);
    }

    curl_url_cleanup(url);
    return resp;
}

consul_response_t *consul_client_mkdir(consul_client_t *client, const char *key) {
    consul_request_t *req;
    consul_response_t *resp;
    CURLU *url;
    char *folder;

    folder = consul_ensure_folder(key);
    url = consul_url_create(CONSUL_API_VERSION, CONSUL_KEYS, folder);
    req = consul_client_request_create(client, CONSUL_HTTP_PUT, url, NULL);
    resp = consul_cluster_request(client, req);
    if (resp) {
        consul_response_parse(resp, consul_parse_success);
    }

    curl_url_cleanup(url);
    free(folder);
    return resp;
}

consul_response_t *consul_client_rmdir(consul_client_t *client, const char *key, int recursive) {
    consul_request_t *req;
    consul_response_t *resp;
    CURLU *url;
    char *folder;

    folder = consul_ensure_folder(key);
    url = consul_url_create(CONSUL_API_VERSION, CONSUL_KEYS, folder);
    if (recursive){
        curl_url_set(url, CURLUPART_QUERY, "recursive=true", CURLU_APPENDQUERY);
    }
    req = consul_client_request_create(client, CONSUL_HTTP_DELETE, url, NULL);
    resp = consul_cluster_request(client, req);
    if (resp) {
        consul_response_parse(resp, consul_parse_success);
    }

    curl_url_cleanup(url);
    free(folder);
    return resp;
}
