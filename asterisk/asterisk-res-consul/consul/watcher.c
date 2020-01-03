#include <stdlib.h>
#include <string.h>

#include "consul.h"

static CURLU* consul_watcher_build_url(consul_client_t *client, consul_watcher_t *watcher) {
    CURLU* url = consul_url_create(CONSUL_API_VERSION, watcher->type, watcher->key);
    if (!url)
        return NULL;

    char wait_param[64];
    snprintf(wait_param, 64, "wait=%ds", watcher->wait_timeout);
    curl_url_set(url, CURLUPART_QUERY, wait_param, CURLU_APPENDQUERY);

    if (watcher->index) {
        char index_param[64];
        snprintf(index_param, 64, "index=%d", watcher->index);
        curl_url_set(url, CURLUPART_QUERY, index_param, CURLU_APPENDQUERY);
    }

    if (watcher->recursive) {
        curl_url_set(url, CURLUPART_QUERY, "recurse=true", CURLU_APPENDQUERY);
    }

    if (watcher->keys) {
        curl_url_set(url, CURLUPART_QUERY, "keys=true", CURLU_APPENDQUERY);
    }

    return url;
}

consul_watcher_t* consul_watcher_create(consul_client_t *client, enum CONSUL_API_TYPE type, const char *key, int recursive, int keys, int initial, consul_watcher_callback_t cb, void *userdata, consul_response_parser parser, int wait_timeout) {
    consul_watcher_t* watch = (consul_watcher_t*) calloc(1, sizeof(consul_watcher_t));

    if (watch) {
        watch->client = client;
        watch->type = type;
        watch->key = key;
        watch->curl = curl_easy_init();
        watch->recursive = recursive;
        watch->keys = keys;
        watch->callback = cb;
        watch->wait_timeout = wait_timeout;
        watch->userdata = userdata;
        watch->parser = parser;
        watch->index = 1;

        watch->request = consul_client_request_create_get(client, key, recursive, keys);
        watch->response = consul_cluster_request(client, watch->request);
        if (watch->response) {
            consul_response_parse(watch->response, parser);
            if (initial) {
                cb(watch->response, userdata);
            }
            watch->index = watch->response->modify_index;
        }

        consul_watcher_reset(watch);
    }

    return watch;
}

int consul_watcher_reset(consul_watcher_t *watcher) {
    CURL* curl = watcher->curl;

    if (watcher->request->url)
        free(watcher->request->url);

    watcher->request->url = consul_watcher_build_url(watcher->client, watcher);

    consul_response_reset(watcher->response);

    consul_request_set_server(watcher->request, watcher->client->servers[watcher->client->leader]);

    consul_request_setopt(watcher->request, watcher->response, curl);

    curl_easy_setopt(curl, CURLOPT_NOSIGNAL, 1L);
    curl_easy_setopt(curl, CURLOPT_PRIVATE, watcher);

    return 0;
}

static int consul_check_watchers(consul_client_t *cli, CURLM *mcurl) {
    uint index = 0;
    int error = 0;
    int ignore;
    CURLMsg *msg;
    CURL *curl;
    consul_watcher_t *watcher;
    consul_response_t *resp;

    while ((msg = curl_multi_info_read(mcurl, &ignore)) != NULL) {
        if (msg->msg == CURLMSG_DONE) {
            curl = msg->easy_handle;
            curl_easy_getinfo(curl, CURLINFO_PRIVATE, &watcher);

            resp = watcher->response;
            index = watcher->index;
            if (msg->data.result != CURLE_OK) {
                if (watcher->attempts > 1) {
                    cli->leader = (cli->leader + 1) % cli->server_count;
                    watcher->attempts--;
                    error = ERROR_REQUEST_FAILED;
                } else if (watcher->attempts == 1) {
                    watcher->attempts--;
                    error = resp->err->ecode = ERROR_CLUSTER_FAILED;
                }
            }

            if (resp->err && resp->err->ecode >= 100 && resp->err->ecode < 500) {
                consul_response_parse(resp, watcher->parser);

                if (watcher->callback && resp->modify_index > index) {
                    error = watcher->callback(resp, watcher->userdata);
                }

                watcher->index = resp->modify_index;
            }

            if (!error) {
                curl_multi_remove_handle(mcurl, curl);
                consul_watcher_reset(watcher);
                curl_multi_add_handle(mcurl, watcher->curl);
                continue;
            }

            curl_multi_remove_handle(mcurl, curl);
            consul_watcher_destroy(watcher);
        }
    }

    return error;
}

int consul_multi_watch(consul_client_t *client, consul_watcher_t **watchers) {
    int              maxfd, left, error;
    long             backoff, backoff_max;
    consul_watcher_t *watcher;
    CURLM            *mcurl;
    CURLMcode        mc;

    struct timeval tv;

    mcurl = curl_multi_init();
    while ((watcher = *watchers++)) {
        curl_easy_setopt(watcher->curl, CURLOPT_PRIVATE, watcher);
        curl_multi_add_handle(mcurl, watcher->curl);
    }

    backoff = 100;
    backoff_max = 1000;

    for(;;) {
        mc = curl_multi_perform(mcurl, &left);
        if (mc == CURLM_OK) {
            mc = curl_multi_wait(mcurl, NULL, 0, 1000, &maxfd);
        }
        if (mc != CURLM_OK) {
            fprintf(stderr, "error curl_multi_perform: %s\n", curl_multi_strerror(mc));
            break;
        }

        error = consul_check_watchers(client, mcurl);
        if (error || left == 0) {
            if (backoff < backoff_max) {
                backoff = 2 * backoff;
            } else {
                 backoff = backoff_max;
            }

            tv.tv_sec = backoff/1000;
            tv.tv_usec = (backoff%1000) * 1000;
            select(1, 0, 0, 0, &tv);
        }
    }

    curl_multi_cleanup(mcurl);
    return mc != CURLM_OK;
}

void consul_watcher_destroy(consul_watcher_t* watch) {
    if (watch->curl)
        curl_easy_cleanup(watch->curl);
    if (watch->request)
        consul_request_cleanup(watch->request);
    if (watch->response)
        consul_response_cleanup(watch->response);
    free(watch);
}
