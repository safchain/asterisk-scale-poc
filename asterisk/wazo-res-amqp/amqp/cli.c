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
 * \brief Command line for AMQP.
 * \author David M. Lee, II <dlee@digium.com>
 */

#include "asterisk.h"


#include "asterisk/cli.h"
#include "asterisk/amqp.h"
#include "internal.h"

#define CLI_NAME_WIDTH 15
#define CLI_URL_WIDTH 25
#define CLI_STATE_WIDTH 15

static int cli_show_connection_summary(void *obj, void *arg, int flags)
{
	struct ast_cli_args *a = arg;
	struct amqp_conf_connection *conf_cxn = obj;
	struct ast_amqp_connection *cxn = ast_amqp_get_connection(conf_cxn->name);

	const char *state = "disconnected";
	if (cxn && cxn->state) {
		state = "connected";
	}

	ast_cli(a->fd, "%-*s %-*s %-*s\n",
			CLI_NAME_WIDTH, conf_cxn->name,
			CLI_URL_WIDTH, conf_cxn->url, CLI_STATE_WIDTH, state);

	return 0;
}

static char *cli_show(struct ast_cli_entry *e, int cmd, struct ast_cli_args *a)
{
	RAII_VAR(struct amqp_conf *, conf, NULL, ao2_cleanup);

	switch (cmd) {
	case CLI_INIT:
		e->command = "amqp show status";
		e->usage =
			"usage: amqp show status\n" "	 Shows all AMQP settings and status\n";
		return NULL;
	case CLI_GENERATE:
		return NULL;
	default:
		break;
	}

	if (a->argc != 3) {
		return CLI_SHOWUSAGE;
	}

	conf = amqp_config_get();
	if (!conf) {
		ast_cli(a->fd, "Error getting AMQP configuration\n");
		return CLI_FAILURE;
	}

	if (!conf->general->enabled) {
		ast_cli(a->fd, "AMQP disabled\n");
		return NULL;
	}

	ast_cli(a->fd, "Connections:\n");
	ast_cli(a->fd, "%-*s %-*s %-*s\n",
			CLI_NAME_WIDTH, "Name", CLI_URL_WIDTH, "URL", CLI_STATE_WIDTH, "State");
	ao2_callback(conf->connections, OBJ_NODATA, cli_show_connection_summary, a);

	return NULL;
}

static char *cli_complete_connection(const char *line, const char *word, int state)
{
	RAII_VAR(struct amqp_conf *, conf, amqp_config_get(), ao2_cleanup);
	struct amqp_conf_connection *cxn_conf;
	int which = 0;
	int wordlen = strlen(word);
	char *c = NULL;
	struct ao2_iterator i;

	if (!conf) {
		ast_log(LOG_ERROR, "Error getting AMQP configuration\n");
		return NULL;
	}

	i = ao2_iterator_init(conf->connections, 0);
	while ((cxn_conf = ao2_iterator_next(&i))) {
		if (!strncasecmp(word, cxn_conf->name, wordlen) && ++which > state) {
			c = ast_strdup(cxn_conf->name);
		}

		ao2_cleanup(cxn_conf);
		if (c) {
			break;
		}
	}
	ao2_iterator_destroy(&i);

	return c;
}

static char *cli_show_connection(struct ast_cli_entry *e, int cmd, struct ast_cli_args *a)
{
	RAII_VAR(struct amqp_conf *, conf, NULL, ao2_cleanup);
	RAII_VAR(struct amqp_conf_connection *, cxn_conf, NULL, ao2_cleanup);

	switch (cmd) {
	case CLI_INIT:
		e->command = "amqp show connection";
		e->usage = "usage: amqp show connection <name>\n" "	 Shows AMQP connection\n";
		return NULL;
	case CLI_GENERATE:
		if (a->pos > 3) {
			return NULL;
		}
		return cli_complete_connection(a->line, a->word, a->n);
	default:
		break;
	}

	if (a->argc != 4) {
		return CLI_SHOWUSAGE;
	}

	conf = amqp_config_get();
	if (!conf) {
		ast_cli(a->fd, "Error getting AMQP configuration\n");
		return CLI_FAILURE;
	}

	cxn_conf = ao2_find(conf->connections, a->argv[3], OBJ_SEARCH_KEY);
	if (!cxn_conf) {
		ast_cli(a->fd, "No connection named %s\n", a->argv[3]);
	}

	ast_cli(a->fd, "Name:           %s\n", cxn_conf->name);
	ast_cli(a->fd, "URL:            %s\n", cxn_conf->url);
	ast_cli(a->fd, "Max frame size: %d bytes\n", cxn_conf->max_frame_bytes);
	if (cxn_conf->heartbeat_seconds) {
		ast_cli(a->fd, "Heartbeat:      %d seconds\n", cxn_conf->heartbeat_seconds);
	} else {
		ast_cli(a->fd, "Heartbeat:      disabled\n");
	}

	struct ast_amqp_connection *cxn = ast_amqp_get_connection(cxn_conf->name);

	const char *state = "disconnected";
	if (cxn && cxn->state) {
		state = "connected";
	}
	ast_cli(a->fd, "State:          %s\n", state);

	return NULL;
}

static char *cli_test_send(struct ast_cli_entry *e, int cmd, struct ast_cli_args *a)
{
	RAII_VAR(struct ast_amqp_connection *, cxn, NULL, ao2_cleanup);
	amqp_basic_properties_t props = {
		._flags = AMQP_BASIC_DELIVERY_MODE_FLAG,
		.delivery_mode = 2,		/* persistent delivery mode */
	};

	switch (cmd) {
	case CLI_INIT:
		e->command = "amqp test send connection";
		e->usage =
			"usage: amqp test send connection <name> queue <queue> message <message>\n"
			"       Sends a message to the specified queue (routing key)\n";
		return NULL;
	case CLI_GENERATE:
		switch (a->pos) {
		case 4:
			return cli_complete_connection(a->line, a->word, a->n);
		case 5:
			return a->n == 0 ? ast_strdup("queue") : NULL;
		case 7:
			return a->n == 0 ? ast_strdup("message") : NULL;
		default:
			return NULL;
		}
	default:
		break;
	}

	if (a->argc != 9) {
		return CLI_SHOWUSAGE;
	}

	if (strcasecmp(a->argv[7], "message") != 0) {
		return CLI_SHOWUSAGE;
	}

	if (strcasecmp(a->argv[5], "queue") != 0) {
		return CLI_SHOWUSAGE;
	}

	cxn = ast_amqp_get_or_create_connection(a->argv[4]);
	if (!cxn) {
		ast_cli(a->fd, "No connection named %s\n", a->argv[4]);
		return NULL;
	}

	if (ast_amqp_basic_publish(cxn, amqp_cstring_bytes(""), amqp_cstring_bytes(a->argv[6]), 0,	/* mandatory */
							   0,	/* immediate */
							   &props, amqp_cstring_bytes(a->argv[8])) != 0) {
		ast_cli(a->fd, "Error sending message\n");
		return NULL;
	}

	ast_cli(a->fd, "Message sent successfully\n");
	return NULL;
}

static struct ast_cli_entry amqp_cli[] = {
	AST_CLI_DEFINE(cli_show, "Show AMQP settings"),
	AST_CLI_DEFINE(cli_show_connection, "Show AMQP connection"),
	AST_CLI_DEFINE(cli_test_send, "Test sending a message"),
};

int amqp_cli_register(void)
{
	return ast_cli_register_multiple(amqp_cli, ARRAY_LEN(amqp_cli));
}

int amqp_cli_unregister(void)
{
	return ast_cli_unregister_multiple(amqp_cli, ARRAY_LEN(amqp_cli));
}
