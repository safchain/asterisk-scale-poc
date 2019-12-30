/*
 * Asterisk -- An open source telephony toolkit.
 *
 * Copyright 2015-2017 The Wazo Authors  (see the AUTHORS file)
 *
 * David M. Lee, II <dlee@digium.com>
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
 */

/*! \file
 *
 * \brief Configuration for AMQP.
 * \author David M. Lee, II <dlee@digium.com>
 */

#include "asterisk.h"


#include "asterisk/config_options.h"
#include "internal.h"

#include <amqp.h>

/*! \brief Locking container for safe configuration access. */
static AO2_GLOBAL_OBJ_STATIC(confs);

static struct aco_type general_option = {
	.type = ACO_GLOBAL,
	.name = "general",
	.item_offset = offsetof(struct amqp_conf, general),
	.category = "^general$",
	.category_match = ACO_WHITELIST,
};

static struct aco_type *general_options[] = ACO_TYPES(&general_option);

static void *amqp_conf_connection_alloc(const char *cat);
static void *amqp_conf_connection_find(struct ao2_container *tmp_container,
									   const char *cat);

static struct aco_type connection_option = {
	.type = ACO_ITEM,
	.name = "connection",
	.category_match = ACO_BLACKLIST,
	.category = "^general$",
	.item_alloc = amqp_conf_connection_alloc,
	.item_find = amqp_conf_connection_find,
	.item_offset = offsetof(struct amqp_conf, connections),
};

static struct aco_type *connection_options[] = ACO_TYPES(&connection_option);

#define CONF_FILENAME "amqp.conf"

/*! \brief The conf file that's processed for the module. */
static struct aco_file conf_file = {
	/*! The config file name. */
	.filename = CONF_FILENAME,
	/*! The mapping object types to be processed. */
	.types = ACO_TYPES(&general_option, &connection_option),
};

static int amqp_conf_connection_sort_cmp(const void *obj_left, const void *obj_right,
										 int flags);

static void conf_dtor(void *obj)
{
	struct amqp_conf *conf = obj;

	ao2_cleanup(conf->general);
	ao2_cleanup(conf->connections);
}

static void *conf_alloc(void)
{
	RAII_VAR(struct amqp_conf *, conf, NULL, ao2_cleanup);

	conf = ao2_alloc_options(sizeof(*conf), conf_dtor, AO2_ALLOC_OPT_LOCK_NOLOCK);
	if (!conf) {
		return NULL;
	}

	conf->general = ao2_alloc_options(sizeof(*conf->general), NULL,
									  AO2_ALLOC_OPT_LOCK_NOLOCK);
	if (!conf->general) {
		return NULL;
	}
	aco_set_defaults(&general_option, "general", conf->general);

	conf->connections = ao2_container_alloc_rbtree(AO2_ALLOC_OPT_LOCK_NOLOCK,
												   AO2_CONTAINER_ALLOC_OPT_DUPS_REPLACE,
												   amqp_conf_connection_sort_cmp, NULL);
	if (!conf->connections) {
		return NULL;
	}

	return ao2_bump(conf);
}

static int validate_connections(void);

CONFIG_INFO_STANDARD(cfg_info, confs, conf_alloc,.files =
					 ACO_FILES(&conf_file),.pre_apply_config = validate_connections,);

static int validate_connection_cb(void *obj, void *arg, int flags)
{
	struct amqp_conf_connection *cxn_conf = obj;
	int *validation_res = arg;

	/* Copy the URL, so we can copy it non-destructively */
	cxn_conf->parsed_url = ast_strdup(cxn_conf->url);
	if (!cxn_conf->parsed_url) {
		*validation_res = -1;
		return -1;
	}

	amqp_default_connection_info(&cxn_conf->connection_info);
	if (amqp_parse_url(cxn_conf->parsed_url, &cxn_conf->connection_info) !=
		AMQP_STATUS_OK) {
		ast_log(LOG_ERROR, "%s: invalid url %s\n", cxn_conf->name, cxn_conf->url);
		*validation_res = -1;
		return -1;
	}

	/* While this could be intentional, this is probably an error */
	if (strlen(cxn_conf->connection_info.vhost) == 0) {
		ast_log(LOG_WARNING, "%s: vhost in url is blank\n", cxn_conf->url);
	}

	if (cxn_conf->max_frame_bytes < AMQP_FRAME_MIN_SIZE) {
		ast_log(LOG_WARNING, "%s: invalid max_frame_bytes %d\n",
				cxn_conf->name, cxn_conf->max_frame_bytes);
		cxn_conf->max_frame_bytes = AMQP_FRAME_MIN_SIZE;
	}

	if (cxn_conf->heartbeat_seconds < 0) {
		ast_log(LOG_WARNING, "%s: invalid heartbeat_seconds %d\n",
				cxn_conf->name, cxn_conf->heartbeat_seconds);
		cxn_conf->heartbeat_seconds = 0;
	}

	return 0;
}

static int validate_connections(void)
{
	int validation_res = 0;

	struct amqp_conf *conf = aco_pending_config(&cfg_info);
	if (!conf) {
		ast_log(LOG_ERROR, "Error obtaining config from amqp.conf\n");
		return 0;
	}

	if (!conf->general->enabled) {
		ast_log(LOG_NOTICE, "AMQP disabled\n");
		return 0;
	}

	ast_debug(3, "Building %d AMQP connections\n",
			  ao2_container_count(conf->connections));
	ao2_callback(conf->connections, OBJ_NODATA, validate_connection_cb, &validation_res);

	return validation_res;
}

static void amqp_conf_connection_dtor(void *obj)
{
	struct amqp_conf_connection *cxn_conf = obj;
	ast_debug(3, "Destroying AMQP connection %s\n", cxn_conf->name);

	ast_string_field_free_memory(cxn_conf);
	ast_free(cxn_conf->parsed_url);
}

static void *amqp_conf_connection_alloc(const char *cat)
{
	RAII_VAR(struct amqp_conf_connection *, cxn_conf, NULL, ao2_cleanup);

	ast_debug(3, "Building AMQP connection %s\n", cat);

	if (!cat) {
		return NULL;
	}

	cxn_conf = ao2_alloc(sizeof(*cxn_conf), amqp_conf_connection_dtor);
	if (!cxn_conf) {
		return NULL;
	}

	if (ast_string_field_init(cxn_conf, 64) != 0) {
		return NULL;
	}

	if (ast_string_field_set(cxn_conf, name, cat) != 0) {
		return NULL;
	}

	ao2_ref(cxn_conf, +1);
	return cxn_conf;
}

static void *amqp_conf_connection_find(struct ao2_container *tmp_container,
									   const char *cat)
{
	if (!cat) {
		return NULL;
	}

	return ao2_find(tmp_container, cat, OBJ_KEY);
}

int amqp_conf_connection_sort_cmp(const void *obj_left, const void *obj_right, int flags)
{
	const struct amqp_conf_connection *cxn_conf_left = obj_left;

	if (flags & OBJ_PARTIAL_KEY) {
		const char *key_right = obj_right;
		return strncasecmp(cxn_conf_left->name, key_right, strlen(key_right));
	} else if (flags & OBJ_KEY) {
		const char *key_right = obj_right;
		return strcasecmp(cxn_conf_left->name, key_right);
	} else {
		const struct amqp_conf_connection *cxn_conf_right = obj_right;
		const char *key_right = cxn_conf_right->name;
		return strcasecmp(cxn_conf_left->name, key_right);
	}
}

static int process_config(int reload)
{
	switch (aco_process_config(&cfg_info, reload)) {
	case ACO_PROCESS_ERROR:
		return -1;
	case ACO_PROCESS_OK:
	case ACO_PROCESS_UNCHANGED:
		break;
	}

	return 0;
}

int amqp_config_init(void)
{
	/* Capture default values in static strings, b/c config framework just
	 * holds onto the pointer. Should be okay, since these are constant
	 * values */
	static char default_frame_size_str[12];
	static char default_heartbeat_str[12];

	snprintf(default_frame_size_str, sizeof(default_frame_size_str),
			 "%d", AMQP_DEFAULT_FRAME_SIZE);

	snprintf(default_heartbeat_str, sizeof(default_heartbeat_str),
			 "%d", AMQP_DEFAULT_HEARTBEAT);

	if (aco_info_init(&cfg_info) != 0) {
		ast_log(LOG_ERROR, "Failed to initialize config\n");
		aco_info_destroy(&cfg_info);
		return -1;
	}

	aco_option_register(&cfg_info, "enabled", ACO_EXACT, general_options,
						"yes", OPT_BOOL_T, 1, FLDSET(struct amqp_conf_general, enabled));

	aco_option_register(&cfg_info, "type", ACO_EXACT, connection_options,
						NULL, OPT_NOOP_T, 0, 0);
	aco_option_register(&cfg_info, "password", ACO_EXACT,
						connection_options, "", OPT_STRINGFIELD_T, 0,
						STRFLDSET(struct amqp_conf_connection, password));
	aco_option_register(&cfg_info, "url", ACO_EXACT, connection_options, "",
						OPT_STRINGFIELD_T, 0,
						STRFLDSET(struct amqp_conf_connection, url));

	aco_option_register(&cfg_info, "max_frame_bytes", ACO_EXACT,
						connection_options, default_frame_size_str, OPT_INT_T, 0,
						FLDSET(struct amqp_conf_connection, max_frame_bytes));

	aco_option_register(&cfg_info, "heartbeat_seconds", ACO_EXACT,
						connection_options, default_heartbeat_str, OPT_INT_T, 0,
						FLDSET(struct amqp_conf_connection, heartbeat_seconds));

	return process_config(0);
}

int amqp_config_reload(void)
{
	return process_config(1);
}

void amqp_config_destroy(void)
{
	aco_info_destroy(&cfg_info);
	ao2_global_obj_release(confs);
}

struct amqp_conf *amqp_config_get(void)
{
	struct amqp_conf *res = ao2_global_obj_ref(confs);
	if (!res) {
		ast_log(LOG_ERROR, "Error obtaining config from " CONF_FILENAME "\n");
	}
	return res;
}

struct amqp_conf_connection *amqp_config_get_connection(const char *name)
{
	RAII_VAR(struct amqp_conf *, conf, NULL, ao2_cleanup);
	conf = amqp_config_get();
	if (!conf) {
		return NULL;
	}

	return ao2_find(conf->connections, name, OBJ_SEARCH_KEY);
}
