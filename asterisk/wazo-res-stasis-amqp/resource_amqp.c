/*
 * Asterisk -- An open source telephony toolkit.
 *
 * Copyright (C) 2019 The Wazo Authors  (see the AUTHORS file)
 *
 * Nicolaos Ballas
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
 * \brief /api-docs/amqp.{format} implementation- AMQP resources
 *
 * \author Nicolaos Ballas
 */

#include "asterisk.h"

#include "resource_amqp.h"
#include "asterisk/stasis_app.h"
#include "asterisk/stasis_amqp.h"

void ast_ari_amqp_stasis_subscribe(struct ast_variable *headers,
								   struct ast_ari_amqp_stasis_subscribe_args *args,
								   struct ast_ari_response *response)
{
	const char *app_name = args->application_name;

	if (!app_name) {
		ast_ari_response_error(response, 400, "Invalid argument",
							   "No application specified");
		return;
	}

	int res = ast_subscribe_to_stasis(app_name);
	if (res == -1) {
		ast_ari_response_error(response, 409, "Application already exists",
							   "The application's name must be unique");
		return;
	} else if (res != 0) {
		ast_ari_response_error(response, 500, "Error", "Unable to allocate json");
		return;
	}
	ast_ari_response_no_content(response);
}
