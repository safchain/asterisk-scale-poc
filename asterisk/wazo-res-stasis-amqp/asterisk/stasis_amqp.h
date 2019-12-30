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

#ifndef ASTERISK_STASIS_AMQP_H
#define ASTERISK_STASIS_AMQP_H

int ast_subscribe_to_stasis(const char *app_name);

int ast_unsubscribe_from_stasis(const char *app_name);

#endif //ASTERISK_STASIS_AMQP_H
