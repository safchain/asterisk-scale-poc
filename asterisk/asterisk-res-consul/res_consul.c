/*
 * Asterisk -- An open source telephony toolkit.
 *
 * Copyright (C) 2019, The Wazo Authors (see the AUTHORS file)
 *
 * Sylvain Baubeau <sbaubeau@wazo.io>
 *
 * See http://www.asterisk.org for more information about
 * the Asterisk project. Please do not directly contact
 * any of the maintainers of this project for assistance;
 * the project provides a web site, mailing lists and IRC
 * channels for your use.
 *
 * This program is free software, distributed under the terms of
 * the GNU General Public License Version 2. See the LICENSE file
 * at the top of the source tree.
 *
 * Please follow coding guidelines
 * https://wiki.asterisk.org/wiki/display/AST/Coding+Guidelines
 */

/*! \file
 *
 * \brief Consul module ressource
 *
 * \author\verbatim Sylvain Baubeau <sbaubeau@wazo.io> \endverbatim
 *
 * This is a resource to access Consul from Asterisk
 * \ingroup applications
 */

/*! \li \ref res_consul.c uses configuration file \ref res_consul.conf
 * \addtogroup configuration_file Configuration Files
 */

/*!
 * \page res_consul.conf res_consul.conf
 * \verbinclude res_consul.conf.sample
 */

/*** MODULEINFO
    <defaultenabled>no</defaultenabled>
    <depend>curl</depend>
    <support_level>extended</support_level>
 ***/

/*! \requirements
 *
 * libcurl - http://curl.haxx.se/libcurl/c
 * jansson - http://www.digip.org/jansson/
 * asterisk - http://asterisk.org
 *
 * Build:
 *
 * make
 * make install
 * make samples
 *
 */

#include "asterisk.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <net/if.h>
#include <arpa/inet.h>
#include <curl/curl.h>

#include "asterisk/module.h"
#include "asterisk/config.h"
#include "asterisk/json.h"
#include "asterisk/uuid.h"
#include "asterisk/cli.h"
#include "asterisk/manager.h"
#include "asterisk/strings.h"
#include "asterisk/threadpool.h"

#include "consul/consul.h"

#include "asterisk/consul.h"

/*** DOCUMENTATION
    <configInfo name="res_consul" language="en_US">
        <synopsis>Consul client.</synopsis>
        <configFile name="res_consul.conf">
            <configObject name="general">
                <synopsis>Global configuration settings</synopsis>
                <configOption name="enabled">
                    <synopsis>Enable/disable the Consul module</synopsis>
                </configOption>
            </configObject>
            <configObject name="connection">
                <synopsis>Per-connection configuration settings</synopsis>
                <configOption name="type">
                   <synopsis>Define this configuration section as a connection.</synopsis>
                   <description>
                       <enumlist>
                           <enum name="connection"><para>Configure this section as a <replaceable>connection</replaceable></para></enum>
                       </enumlist>
                   </description>
               </configOption>
               <configOption name="url">
                   <synopsis>URL to connect to</synopsis>
                   <description>
                       <para>URL of the AMQP server to connect to. Is of the form <literal>amqp://[$USERNAME[:$PASSWORD]@]$HOST[:$PORT]/[$VHOST]</literal></para>
                   </description>
               </configOption>
               <configOption name="password">
                   <synopsis>Password for AMQP login</synopsis>
                   <description>
                       <para>When the AMQP server requires login, specified the login password</para>
                   </description>
               </configOption>
               <configOption name="max_frame_bytes">
                   <synopsis>The maximum size of an AMQP frame on the wire to request of the broker for this connection.</synopsis>
                   <description>
                       <para>4096 is the minimum size, 2^31-1 is the maximum</para>
                   </description>
               </configOption>
               <configOption name="heartbeat_seconds">
                   <synopsis>the number of seconds between heartbeat frames to request of the broker</synopsis>
                   <description>
                       <para>A value of 0 disables heartbeats.</para>
                   </description>
               </configOption>
           </configObject>
        </configFile>
    </configInfo>
 ***/

#define MAX_URL_LENGTH 512
#define CONSUL_WATCH_TIMEOUT 5

static struct consul_client_t *active_client;

struct ast_threadpool* watcher_thread_pool;

typedef struct consul_client_t ast_consul_client;

typedef struct consul_check_t ast_consul_service_check;

struct consul_config {
    int enabled;
    char host[256];
    int port;
    char token[256];
};

static struct consul_config global_config = {
    .enabled = 1,
    .host = "127.0.0.1",
    .port = 8500,
    .token = ""
};

static const char config_file[] = "res_consul.conf";

/*! \brief Function called to load or reload the configuration file */
static void load_config(int reload)
{
    struct ast_config *cfg = NULL;
    struct ast_flags config_flags = { reload ? CONFIG_FLAG_FILEUNCHANGED : 0 };
    struct ast_variable *v;
    int enabled = 1;

    if (!(cfg = ast_config_load(config_file, config_flags)) || cfg == CONFIG_STATUS_FILEINVALID) {
        ast_log(LOG_ERROR, "res_consul configuration file '%s' not found\n", config_file);
        return;
    } else if (cfg == CONFIG_STATUS_FILEUNCHANGED) {
        return;
    }

    for (v = ast_variable_browse(cfg, "general"); v; v = v->next) {
        if (!strcasecmp(v->name, "enabled")) {
            if (ast_true(v->value) == 0) {
                enabled = 0;
            }
            global_config.enabled = enabled;
        }
    }

    for (v = ast_variable_browse(cfg, "consul"); v; v = v->next) {
        if (!strcasecmp(v->name, "host")) {
            ast_copy_string(global_config.host, v->value, strlen(v->value) + 1);
        } else if (!strcasecmp(v->name, "port")) {
            global_config.port = atoi(v->value);
        } else if (!strcasecmp(v->name, "token")) {
            ast_copy_string(global_config.token, v->value, strlen(v->value) + 1);
        }
    }

    ast_config_destroy(cfg);

    return;
}

/*! \brief Function called to load the resource */
static int load_res(int start)
{
    const char *servers[2];
    char server[MAX_URL_LENGTH];

    snprintf(server, MAX_URL_LENGTH, "http://%s:%d", global_config.host, global_config.port);
    servers[0] = server; servers[1] = NULL;

    if ((active_client = consul_client_create(1, servers)) == NULL) {
        ast_log(LOG_ERROR, "failed to create client");
        return 1;
    }

    return 0;
}

int ast_consul_service_register(const char* id,
                                const char *name,
                                const char *discovery_ip,
                                int discovery_port,
                                const char **tags,
                                const char **meta,
                                struct ast_consul_service_check **checks) {
    consul_service_t service;
    int success;

    service.id = id;
    service.name = name;
    service.address = discovery_ip;
    service.port = discovery_port;
    service.tags = tags;
    service.meta = meta;
    service.checks = NULL;

    int i;
    int checks_count = 0;
    if (checks) {
        while (checks[checks_count])
            checks_count++;

        service.checks = (consul_check_t**) ast_calloc(checks_count+1, sizeof(consul_check_t*));
        for (i = 0; i < checks_count; i++) {
            service.checks[i] = (struct consul_check_t*) ast_calloc(1, sizeof(consul_check_t));
            service.checks[i]->http = checks[i]->http;
            service.checks[i]->interval = checks[i]->interval;
        }
    }

    consul_response_t *response = consul_service_register(active_client, &service);
    success = consul_response_is_success(response);

    if (!success) {
        ast_log(LOG_ERROR, "failed to register service %s\n", response->err ? response->err->message : "unknown error");
    }

    consul_response_cleanup(response);

    for (i = 0; i < checks_count; i++) {
        ast_free(service.checks[i]);
    }
    ast_free(service.checks);

    return success;
}

int ast_consul_service_deregister(const char *id) {
    return consul_response_is_success(consul_service_deregister(active_client, id));
}

int ast_consul_service_set_maintenance(const char *id, int state, const char *reason) {
    return consul_response_is_success(consul_service_set_maintenance(active_client, id, state, reason));
}

static int consul_watcher_thread(void* userdata) {
    int rc;
    consul_watcher_t* watchers[2] = { (consul_watcher_t*) userdata, NULL };

    if ((rc = consul_multi_watch(active_client, watchers))) {
        return rc;
    }

    ast_log(LOG_NOTICE, "stopping watcher thread\n");

    consul_watcher_destroy(watchers[0]);

    return 0;
}

static int consul_watch_keys_callback(consul_response_t* response, void* userdata) {
    ast_consul_watch_keys_callback cb = (ast_consul_watch_keys_callback) userdata;
    int success = response->err && (response->err->ecode == 200 || response->err->ecode == 404);

    if (success) {
        cb(response->key_count, response->keys);
    } else {
        ast_log(LOG_ERROR, "watcher error %s\n", response->err->message);
    }
    return 0;
}

int ast_consul_watch_keys(const char *key, ast_consul_watch_keys_callback cb) {
    consul_watcher_t* watcher;

    watcher = consul_watcher_create(active_client, CONSUL_KEYS, key, 1, 1, 1, consul_watch_keys_callback, cb, consul_parse_lsdir_response, CONSUL_WATCH_TIMEOUT);
    if (!watcher) {
        ast_log(LOG_ERROR, "error while registering kv watcher for %s\n", key);
        return -1;
    }

    return ast_threadpool_push(watcher_thread_pool, consul_watcher_thread, watcher);
}

/*! \brief Function called to exec CLI */
static char *consul_cli_settings(struct ast_cli_entry *e, int cmd, struct ast_cli_args *a)
{
    switch (cmd) {
    case CLI_INIT:
        e->command = "consul show settings";
        e->usage =
            "Usage: consul show settings\n"
            "       Get the settings of Consul service.\n\n"
            "       Example:\n"
            "        consul show settings\n";
        return NULL;
    case CLI_GENERATE:
        return NULL;
    }

    ast_cli(a->fd, "\n\nConsul Settings:\n");
    ast_cli(a->fd, "----------------\n");
    ast_cli(a->fd, "Connection: http://%s:%d\n", global_config.host, global_config.port);
    ast_cli(a->fd, "Token: %s\n", global_config.token);
    ast_cli(a->fd, "----\n");

    return NULL;
}

/*! \brief Function called to define CLI */
static struct ast_cli_entry cli_consul[] = {
    AST_CLI_DEFINE(consul_cli_settings, "Show Consul settings"),
};

static int reload_module(void)
{
    load_config(1);

    return 0;
}

static int unload_module(void)
{
    ast_threadpool_shutdown(watcher_thread_pool);

    consul_client_destroy(active_client);

    return 0;
}

static int load_module(void)
{
    struct ast_threadpool_options threadpool_opts;

    ast_log(LOG_NOTICE, "res_consul loading\n");

    load_config(0);

    if (global_config.enabled == 0) {
        ast_log(LOG_NOTICE, "This module is disabled\n");
        return AST_MODULE_LOAD_DECLINE;
    }

    if (load_res(1)) {
        return AST_MODULE_LOAD_DECLINE;
    }

    ast_cli_register_multiple(cli_consul, ARRAY_LEN(cli_consul));

    threadpool_opts.version = AST_THREADPOOL_OPTIONS_VERSION;
    threadpool_opts.idle_timeout = 15;
    threadpool_opts.auto_increment = 1;
    threadpool_opts.initial_size = 0;
    threadpool_opts.max_size = 10;
    threadpool_opts.thread_start = threadpool_opts.thread_end = NULL;

    watcher_thread_pool = ast_threadpool_create("consul-watchers", NULL, &threadpool_opts);
    if (!watcher_thread_pool) {
        ast_log(LOG_ERROR, "Failed to create Consul watcher thread pool");
        return AST_MODULE_LOAD_DECLINE;
    }

    return AST_MODULE_LOAD_SUCCESS;
}

AST_MODULE_INFO(ASTERISK_GPL_KEY, AST_MODFLAG_GLOBAL_SYMBOLS | AST_MODFLAG_LOAD_ORDER, "Asterisk Consul module",
    .support_level = AST_MODULE_SUPPORT_EXTENDED,
    .load = load_module,
    .unload = unload_module,
    .reload = reload_module,
    .load_pri = AST_MODPRI_APP_DEPEND,
);
