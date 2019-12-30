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

#ifndef _ASTERISK_AMQP_H
#define _ASTERISK_AMQP_H

/*! \file
 * \brief AMQP client
 *
 * \author David M. Lee, II <dlee@digium.com>
 * \since 13.x
 *
 * This file contains the Asterisk API for AMQP. Connections are configured
 * in \c amqp.conf. You can get a connection by name, using \ref
 * ast_amqp_get_or_create_connection().
 *
 * Only publish support is implemented, using \ref ast_amqp_basic_publish().
 *
 * Note that the AMQP protocol has a "channel" feature, which allows
 * multiplexing multiple requests on a single TCP socket. Unfortunately, the
 * underlying \c librabbitmq library is not thread safe, so we couldn't take
 * advantage of this feature. Because of that, and the complications it adds
 * to using the API, we've omitted that feature.
 */

#include <amqp.h>

/*!
 * Opaque handle for the AMQP connection.
 */
struct ast_amqp_connection;

/*!
 * \brief Gets the given AMQP connection.
 *
 * The returned connection is an AO2 managed object, which must be freed with
 * \ref ao2_cleanup().
 *
 * \param name The name of the connection.
 * \return The connection object.
 * \return \c NULL if connection not found, or some other error.
 */
struct ast_amqp_connection *ast_amqp_get_connection(const char *name);

/*!
 * \brief Gets or creates the given AMQP connection.
 *
 * The returned connection is an AO2 managed object, which must be freed with
 * \ref ao2_cleanup().
 *
 * \param name The name of the connection.
 * \return The connection object.
 * \return \c NULL if connection not found, or some other error.
 */
struct ast_amqp_connection *ast_amqp_get_or_create_connection(const char *name);

/*!
 * \brief Publishes a message to a AMQP connection.
 *
 * \param cxn The connection to publish to.
 * \param exchange the exchange on the broker to publish to
 * \param routing_key the routing key (queue) to use when publishing the message
 * \param mandatory indicate to the broker that the message MUST be routed to a
 *                  queue. If the broker cannot do this it should respond with
 *                  a basic.reject method
 * \param immediate indicate to the broker that the message MUST be delivered
 *                  to a consumer immediately. If the broker cannot do this it
 *                  should response with a basic.reject method
 * \param properties Properties of the message (content-type, delivery mode, etc.)
 * \param body The text of the message to send.
 * \return 0 on success.
 * \return -1 on failure.
 */
int ast_amqp_basic_publish(struct ast_amqp_connection *cxn,
						   amqp_bytes_t exchange,
						   amqp_bytes_t routing_key,
						   amqp_boolean_t mandatory,
						   amqp_boolean_t immediate,
						   const amqp_basic_properties_t * properties, amqp_bytes_t body);

#endif /* _ASTERISK_AMQP_H */
