#include <curl/curl.h>
#include <jansson.h>

#define CONSUL_API_VERSION 1
#define MAX_WATCHERS       32
#define MAX_CONSUL_SERVERS 15

#define TOO_MANY_SERVERS -1
#define OUT_OF_MEMORY    -2

#define ERROR_REQUEST_FAILED   1001
#define ERROR_INVALID_RESPONSE 1002
#define ERROR_CLUSTER_FAILED   1003

enum CONSUL_API_TYPE {
    CONSUL_KEYS,
    CONSUL_SERVICES,
    CONSUL_AGENT_REGISTER,
    CONSUL_AGENT_DEREGISTER,
    CONSUL_AGENT_SET_MAINTENANCE
};

enum HTTP_METHOD {
    CONSUL_HTTP_GET,
    CONSUL_HTTP_POST,
    CONSUL_HTTP_PUT,
    CONSUL_HTTP_DELETE,
    CONSUL_HTTP_HEAD,
    CONSUL_HTTP_OPTION
};

struct consul_response_t;
struct consul_request_t;

typedef int (*consul_watcher_callback_t) (struct consul_response_t* response, void *userdata);

typedef int (*consul_response_parser) (struct consul_response_t *response, json_t* root);

typedef struct consul_watcher_t {
    struct consul_client_t*   client;
    CURLM*                    curl;
    int                       server_count;
    int                       recursive;
    int                       index;
    int                       keys;
    enum CONSUL_API_TYPE      type;
    const char*               key;
    int                       wait_timeout;
    int                       attempts;
    consul_watcher_callback_t callback;
    void*                     userdata;
    consul_response_parser    parser;
    struct consul_response_t* response;
    struct consul_request_t*  request;
} consul_watcher_t;

typedef struct consul_server_t {
    char *host;
    char *port;
    char *scheme;
} consul_server_t;

typedef struct consul_client_t {
    consul_server_t** servers;
    int    server_count;
    int leader;
    consul_watcher_t* watchers[MAX_WATCHERS];
    struct {
        int      verbose;
        uint     ttl;
        uint     connect_timeout;
        char*    user;
        char*    password;
        char*    scheme;
    } settings;
} consul_client_t;

typedef struct consul_error_t {
    int ecode;
    char *message;
    char *cause;
} consul_error_t;

typedef struct consul_response_t {
    consul_error_t* err;
    uint index;
    int known_leader;
    int last_contact;
    char *data;
    int data_length;
    int chunked;
    uint modify_index;
    struct {
        int key_count;
        char** keys;
    };
    struct {
        int lock_index;
        uint create_index;
        char* key;
        char *value;
        int flags;
    };
    int success;
} consul_response_t;

typedef struct consul_check_t {
    const char *http;
    int interval;
} consul_check_t;

typedef struct consul_service_t {
    struct {
        char* id;
        char *name;
        char* node;
        char* address;
        int port;
        char **tags;
        char **meta;
    } Node;

    const char* id;
    const char *name;
    const char* node;
    const char* address;
    int port;
    const char **tags;
    const char **meta;
    consul_check_t **checks;
} consul_service_t;

typedef struct consul_request_t {
    enum HTTP_METHOD method;
    CURL *curl;
    CURLU* url;
    const char *data;
    consul_client_t* client;
} consul_request_t;

CURLU* consul_url_create(int version, enum CONSUL_API_TYPE type, const char *path);

consul_server_t* consul_server_create(const char *url);
void consul_server_cleanup(consul_server_t* server);

consul_client_t* consul_client_create(int server_count, const char** servers);
void consul_client_setup_user(consul_client_t* client, const char *user, const char *password);
void consul_client_destroy(consul_client_t* client);
consul_response_t *consul_client_lsdir(consul_client_t *cli, const char *key, int recursive);
consul_response_t* consul_cluster_request(consul_client_t* client, consul_request_t* req);
consul_response_t *consul_client_put(consul_client_t *client, const char *key, char *value);
consul_response_t *consul_client_get(consul_client_t *client, const char *key, int recursive, int keys);
consul_response_t *consul_client_delete(consul_client_t *client, const char *key);
consul_response_t *consul_client_mkdir(consul_client_t *client, const char *key);
consul_response_t *consul_client_rmdir(consul_client_t *client, const char *key, int recursive);
int consul_multi_watch(consul_client_t *client, consul_watcher_t **watchers);

consul_watcher_t* consul_watcher_create(consul_client_t *client, enum CONSUL_API_TYPE type, const char *key, int recursive, int keys, int initial, consul_watcher_callback_t cb, void *userdata, consul_response_parser parser, int wait_timeout);
int consul_watcher_reset(consul_watcher_t *watcher);
void consul_watcher_destroy(consul_watcher_t* watch);

size_t consul_header_callback(char *buffer, size_t size, size_t nitems, void *userdata);
size_t consul_body_callback(void *contents, size_t length, size_t nmemb, void *userp);

consul_request_t* consul_client_request_create(consul_client_t* client, enum HTTP_METHOD method, CURLU* url, const char *data);
consul_request_t* consul_client_request_create_get(consul_client_t *client, const char *key, int recursive, int keys);
void consul_request_set_server(consul_request_t* request, consul_server_t* server);
consul_response_t* consul_request_send(consul_request_t* req);
void consul_request_setopt(consul_request_t* req, consul_response_t* resp, CURL *curl);
void consul_request_cleanup(consul_request_t* request);

consul_response_t* consul_response_create(void);
int consul_response_is_success(consul_response_t *response);
void consul_response_reset(consul_response_t* response);
void consul_response_cleanup(consul_response_t* response);
int consul_response_parse(consul_response_t *response, consul_response_parser parser);

int consul_parse_get_response(consul_response_t* response, json_t* root);
int consul_parse_lsdir_response(consul_response_t* response, json_t* root);

consul_response_t *consul_service_register(consul_client_t* client, consul_service_t* service);
consul_response_t *consul_service_deregister(consul_client_t* client, const char *service_id);
consul_response_t *consul_service_set_maintenance(consul_client_t* client, const char *service_id, int state, const char *reason);
