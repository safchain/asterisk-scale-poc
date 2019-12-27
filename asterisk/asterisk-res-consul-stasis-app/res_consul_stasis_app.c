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
 * \author\verbatim Sylvain Boily <sboily@avencall.com> \endverbatim
 *
 * This is a resource to discovery an Asterisk application via Consul
 * \ingroup applications
 */

/*! \li \ref res_discovery_consul.c uses configuration file \ref res_discovery_consul.conf
 * \addtogroup configuration_file Configuration Files
 */

/*! 
 * \page res_discovery_consul.conf res_discovery_consul.conf
 * \verbinclude res_discovery_consul.conf.sample
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

static char asterisk_eid[18];
struct ao2_container *registered_apps = NULL;

// NOTE(safchain) need to place this is the res_stasis_amqp
// side note, do we want a strong dependency between consul
// and amqp ?
int ast_subscribe_to_stasis(const char *app_name);

static int register_application(const char* app) {
	const char *tags[2] = { asterisk_eid, NULL };
	int res = ast_subscribe_to_stasis(app);
	if (!res) {
		ast_log(LOG_NOTICE, "application %s registered\n", app);
		ast_consul_service_register(
			app,
			app,
			"",
			0,
			tags,
			NULL,
			NULL
		);
	} else {
		ast_log(LOG_NOTICE, "failed to register application %s\n", app);
	}
	return res;
}

static int unregister_application(const char *app) {
	stasis_app_unregister(app);
	ast_log(LOG_NOTICE, "application %s unregistered\n", app);
	ast_consul_service_deregister(app);
	return 0;
}

static int unregister_application_cb(void *obj, void *arg, int flags) {
	const char *app_name = obj;
	ast_str_container_remove(registered_apps, app_name);
	return unregister_application(app_name);
}

static int consul_watch_callback(int app_count, const char **applications) {
	RAII_VAR(struct ao2_container *, existing_apps, NULL, ao2_cleanup);

	ao2_lock(registered_apps);
	existing_apps = ao2_container_clone(registered_apps, OBJ_NOLOCK);
	for (int i = 0; i < app_count; i++) {
		const char *app_name = applications[i];
		void *result = ao2_find(existing_apps, app_name, OBJ_UNLINK | OBJ_SEARCH_KEY);
		ast_log(LOG_NOTICE, "searched for %s in existing app => %p\n", app_name, result);
		if (!result) {
			// NOTE(safchain) quick fix need something cleaner to remove prefix
			if (strncmp(app_name, "applications/", 13) == 0) {
				if (!register_application(app_name + 13)) {
					ast_str_container_add(registered_apps, app_name);
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
	int result = ast_consul_watch_keys("applications/", consul_watch_callback);
	if (!result)
		ast_log(LOG_NOTICE, "registered watcher on Consul kv on path /applications/\n");
	return result;
}

/*! \brief Function called to load or reload the configuration file */
static void load_config(int reload)
{
	return;
}

/*! \brief Function called to load the resource */
static int load_res(int start)
{
	if (start == 1) {
		return consul_register_statis_apps();
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
