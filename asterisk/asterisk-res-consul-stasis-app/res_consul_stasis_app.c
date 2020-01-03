/*
 * Asterisk -- An open source telephony toolkit.
 *
 * Copyright (C) <2015>, Sylvain Boily
 *
 * Sylvain Boily <sylvainboilydroid@gmail.com>
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
 * \brief Consul discovery module ressource
 *
 * \author\verbatim Sylvain Baubeau <sbaubeau@wazo.io> \endverbatim
 *
 * This is a resource to register Stasis applications via Consul
 * \ingroup applications
 */

/*! \li \ref res_consul_stasis_app.c uses configuration file \ref res_consul_stasis_app.conf
 * \addtogroup configuration_file Configuration Files
 */

/*! 
 * \page res_consul_stasis_app.conf res_consul_stasis_app.conf
 * \verbinclude res_consul_stasis_app.conf.sample
 */

/*** MODULEINFO
	<defaultenabled>no</defaultenabled>
	<depend>cuconsulrl</depend>
	<support_level>extended</support_level>
 ***/

/*! \requirements
 *
 * asterisk - http://asterisk.org
 *
 * Build:
 *
 * make
 * make install
 * make samples
 * 
 */

#include "stdlib.h"
#include "stdio.h"

#include "asterisk.h"

#include "asterisk/module.h"
#include "asterisk/config.h"
#include "asterisk/json.h"
#include "asterisk/uuid.h"
#include "asterisk/cli.h"
#include "asterisk/manager.h"
#include "asterisk/strings.h"
#include "asterisk/consul.h"
#include "asterisk/stasis_app.h"

static const char config_file[] = "res_consul_stasis_app.conf";
static const char default_app_prefix[] = "applications/";
char *app_prefix = NULL;
static char asterisk_eid[18];
struct ao2_container *registered_apps = NULL;

// NOTE(safchain) need to place this is the res_stasis_amqp
// side note, do we want a strong dependency between consul
// and amqp ?
int ast_subscribe_to_stasis(const char *app_name);

static int register_application(const char* app_name) {
	const char *tags[2] = { asterisk_eid, NULL };

	int res = ast_subscribe_to_stasis(app_name);
	if (!res) {
		char* service_id = (char*) ast_calloc(1, strlen(app_name) + 7 + sizeof(asterisk_eid));
		sprintf(service_id, "stasis/%s/%s", asterisk_eid, app_name);

		ast_log(LOG_NOTICE, "application %s registered\n", app_name);
		ast_consul_service_register(
			service_id,
			app_name,
			"",
			0,
			tags,
			NULL,
			NULL
		);

		ast_free(service_id);
	} else {
		ast_log(LOG_NOTICE, "failed to register application %s\n", app_name);
	}
	return res;
}

static int unregister_application(const char *app) {
	stasis_app_unregister(app);
	ast_log(LOG_NOTICE, "application %s unregistered\n", app);
	char* service_id = (char*) ast_calloc(1, strlen(app) + 7 + sizeof(asterisk_eid));
	sprintf(service_id, "stasis/%s/%s", asterisk_eid, app);
	ast_consul_service_deregister(service_id);
	ast_free(service_id);
	return 0;
}

static int unregister_application_cb(void *obj, void *arg, int flags) {
	const char *app_name = obj;
	ast_str_container_remove(registered_apps, app_name);
	return unregister_application(app_name);
}

static int consul_watch_callback(int app_count, char **applications) {
	RAII_VAR(struct ao2_container *, existing_apps, NULL, ao2_cleanup);

	ao2_lock(registered_apps);
	existing_apps = ao2_container_clone(registered_apps, OBJ_NOLOCK);

	for (int i = 0; i < app_count; i++) {
		// NOTE(safchain) not sure if we need to bypass or we need to update
		if (strncmp(applications[i], app_prefix, strlen(app_prefix)) == 0) {
			const char *app_name = applications[i] + strlen(app_prefix);
			void *result = ao2_find(existing_apps, app_name, OBJ_UNLINK | OBJ_SEARCH_KEY);
			ast_log(LOG_NOTICE, "searched for %s in existing app => %p\n", app_name, result);
			if (!result) {
				void *app = stasis_app_get_by_name(app_name);
				if (app != NULL) {
					ast_log(LOG_NOTICE, "application %s already registered\n", app_name);
				} else {
					// NOTE(safchain) quick fix need something cleaner to remove prefix
					if (!register_application(app_name)) {
						ast_str_container_add(registered_apps, app_name);
					}
				}
			}
		}
	}

	ao2_callback(existing_apps, 0, unregister_application_cb, NULL);
	ao2_unlock(registered_apps);

	return 0;
}

/*! \brief Function called to register statis applications stored in Consul */
static int consul_register_statis_apps(void) {
	int result = ast_consul_watch_keys(app_prefix, consul_watch_callback);
	if (!result)
		ast_log(LOG_NOTICE, "registered watcher on Consul kv on path /%s\n", app_prefix);
	return result;
}

/*! \brief Function called to load or reload the configuration file */
static void load_config(int reload)
{
	struct ast_config *cfg = NULL;
	struct ast_flags config_flags = { reload ? CONFIG_FLAG_FILEUNCHANGED : 0 };
	struct ast_variable *v;

	if (!(cfg = ast_config_load(config_file, config_flags)) || cfg == CONFIG_STATUS_FILEINVALID) {
		ast_log(LOG_ERROR, "res_consul_stasis_app configuration file '%s' not found\n", config_file);
		return;
	} else if (cfg == CONFIG_STATUS_FILEUNCHANGED) {
		return;
	}

	for (v = ast_variable_browse(cfg, "general"); v; v = v->next) {
		if (!strcasecmp(v->name, "app_prefix")) {
			app_prefix = ast_strdup(v->value);
		}
	}

	ast_config_destroy(cfg);
}

/*! \brief Function called to load the resource */
static int load_res(int start)
{
	if (start == 1) {
		app_prefix = (char*) default_app_prefix;
		return consul_register_statis_apps();
	} else {
		if (app_prefix != default_app_prefix)
			ast_free(app_prefix);
	}

	return AST_MODULE_LOAD_SUCCESS;
}

static int reload_module(void)
{
	load_config(1);
	return 0;
}

static int unload_module(void)
{
	load_res(0);
	return 0;
}

static int load_module(void)
{
	if (!ast_module_check("res_consul.so")) {
		if (ast_load_resource("res_consul.so") != AST_MODULE_LOAD_SUCCESS) {
			ast_log(LOG_ERROR, "Cannot load res_consul, so res_consul_stasis_app cannot be loaded\n");
			return AST_MODULE_LOAD_DECLINE;
		}
	}

	ast_eid_to_str(asterisk_eid, sizeof(asterisk_eid), &ast_eid_default);

	load_config(0);

	registered_apps = ast_str_container_alloc(1);

	if (load_res(1) != AST_MODULE_LOAD_SUCCESS) {
		return AST_MODULE_LOAD_DECLINE;
	}

	return AST_MODULE_LOAD_SUCCESS;
}

AST_MODULE_INFO(ASTERISK_GPL_KEY, AST_MODFLAG_DEFAULT, "Asterisk Statis applications registration from Consul",
	.support_level = AST_MODULE_SUPPORT_EXTENDED,
	.load = load_module,
	.unload = unload_module,
	.reload = reload_module,
	.load_pri = AST_MODPRI_APP_DEPEND,
	.requires = "res_stasis_amqp",
);
