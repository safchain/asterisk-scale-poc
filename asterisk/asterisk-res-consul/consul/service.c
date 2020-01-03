#include "consul.h"

#include <jansson.h>

static json_t* strings_to_json_array(const char** strings) {
    json_t* array = json_array();

    while (*strings) {
        json_array_append(array, json_string(*strings));
        strings++;
    }

    return array;
}

static json_t* strings_to_json_dict(const char** strings) {
    json_t* obj = json_object();

    while (*strings) {
        json_object_set(obj, *strings, json_string(*(strings+1)));
        strings += 2;
    }

    return obj;
}

static json_t* check_to_json_dict(consul_check_t *check) {
    char interval[32];
    snprintf(interval, 32, "%ds", check->interval);
    return json_pack("{s:s?,s:s}", "HTTP", check->http, "Interval", interval);
}

static json_t* checks_to_json_array(consul_check_t **checks) {
    json_t* array = json_array();

    while (*checks) {
        json_array_append(array, check_to_json_dict(*checks));
        checks++;
    }

    return array;
}

consul_response_t *consul_service_register(consul_client_t* client, consul_service_t* service) {
    consul_request_t *req;
    consul_response_t *resp;
    json_t* obj;
    CURLU *url;
    char *dump;

    obj = json_pack("{s:s?,s:s?,s:s?,s:i,s:o*,s:o*,s:o*}",
                    "ID", service->id,
                    "Name", service->name,
                    "Address", service->address,
                    "Port", service->port,
                    "Tags", service->tags ? strings_to_json_array(service->tags) : NULL,
                    "Meta", service->meta ? strings_to_json_dict(service->meta) : NULL,
                    "Checks", service->checks ? checks_to_json_array(service->checks) : NULL);

    dump = json_dumps(obj, 0);
    url = consul_url_create(CONSUL_API_VERSION, CONSUL_AGENT_REGISTER, "");
    req = consul_client_request_create(client, CONSUL_HTTP_PUT, url, dump);
    resp = consul_cluster_request(client, req);
    consul_request_cleanup(req);
    return resp;
}

consul_response_t *consul_service_deregister(consul_client_t* client, const char *service_id) {
    consul_request_t *req;
    consul_response_t *resp;
    CURLU *url;

    url = consul_url_create(CONSUL_API_VERSION, CONSUL_AGENT_DEREGISTER, service_id);
    req = consul_client_request_create(client, CONSUL_HTTP_PUT, url, NULL);
    resp = consul_cluster_request(client, req);
    consul_request_cleanup(req);
    return resp;
}

consul_response_t *consul_service_set_maintenance(consul_client_t* client, const char *service_id, int state, const char *reason) {
    consul_request_t *req;
    consul_response_t *resp;
    CURLU *url;
    char reason_param[4096];

    url = consul_url_create(CONSUL_API_VERSION, CONSUL_AGENT_SET_MAINTENANCE, service_id);
    if (state) {
        curl_url_set(url, CURLUPART_QUERY, "enable=true", CURLU_APPENDQUERY);
    } else {
        curl_url_set(url, CURLUPART_QUERY, "enable=false", CURLU_APPENDQUERY);
    }
    if (reason) {
        snprintf(reason_param, 4096, "reason=%s", reason);
        curl_url_set(url, CURLUPART_QUERY, reason_param, CURLU_APPENDQUERY);
    }

    req = consul_client_request_create(client, CONSUL_HTTP_PUT, url, NULL);
    resp = consul_cluster_request(client, req);
    consul_request_cleanup(req);
    return resp;
}
