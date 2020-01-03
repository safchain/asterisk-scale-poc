/*
 * Asterisk -- An open source telephony toolkit.
 *
 * Copyright 2015-2019 The Wazo Authors (see the AUTHORS file)
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

#ifndef _ASTERISK_CONSUL_H
#define _ASTERISK_CONSUL_H

/*! \file
 * \brief Consul client
 *
 * \author Sylvain Baubeau <sbaubeau@wazo.io>
 * \since 1.x
 *
 * This file contains the Asterisk API for Consul. Connections are configured
 * in \c res_consul.conf.
 *
 */

/*!
 * Opaque handle for the Consul client.
 */
struct ast_consul_client;

/*!
 * Handle for a Consul service check.
 */
struct ast_consul_service_check {
   const char *http;
   int interval;
};

typedef int (*ast_consul_watch_keys_callback) (int key_count, char **keys);

/*!
 * \brief Gets a Consul client.
 *
 * The returned connection is borrowed and therefore doesn't have to be freed.
 *
 * \return The client object.
 * \return \c NULL if client not found, or some other error.
 */
struct ast_consul_client* ast_consul_get_client(void);

/*!
 * \brief Register a service into Consul.
 *
 * \param id Unique ID for this service.
 * \param name Logical name of the service.
 * \param discovery_ip Address of the service.
 * \param discovery_port Port of the service.
 * \param tags Null terminated list of tags to assign to the service.
 * \param meta Null terminated list of metadata to assign to the service.
 * \return 1 on success.
 * \return 0 on failure.
 */
int ast_consul_service_register(const char* id,
                                const char *name,
                                const char *discovery_ip,
                                int discovery_port,
                                const char **tags,
                                const char **meta,
                                struct ast_consul_service_check **checks);

/*!
 * \brief Deregister a service from Consul.
 *
 * \param id Unique ID for this service.
 * \return 1 on success.
 * \return 0 on failure.
 */
int ast_consul_service_deregister(const char *id);

/*!
 * \brief Set maintenance state of a Consul service.
 *
 * \param id ID of the service to put in maintenance mode.
 * \param state Whether to enable or disable maintenance mode.
 * \param reason Text string explaining the reason for placing the node into maintenance mode.
 * \return 1 on success.
 * \return 0 on failure.
 */
int ast_consul_service_set_maintenance(const char *id, int state, const char *reason);

/*!
 * \brief Watch Consul keys
 *
 * \param prefix Keys prefix to watch.
 * \param cb Callback to call.
 * \return 1 on success.
 * \return 0 on failure.
 */
int ast_consul_watch_keys(const char *prefix, ast_consul_watch_keys_callback cb);

#endif /* _ASTERISK_CONSUL_H */
