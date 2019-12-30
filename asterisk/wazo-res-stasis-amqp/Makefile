#
# Makefile for Asterisk stasis to amqp resource
# Copyright 2017-2019 The Wazo Authors  (see the AUTHORS file)
#
# This program is free software, distributed under the terms of
# the GNU General Public License Version 3. See the COPYING file
# at the top of the source tree.
#

ASTLIBDIR:=$(shell awk '/moddir/{print $$3}' /etc/asterisk/asterisk.conf 2> /dev/null)
ifeq ($(strip $(ASTLIBDIR)),)
	MODULES_DIR:=$(INSTALL_PREFIX)/usr/lib/asterisk/modules
else
	MODULES_DIR:=$(INSTALL_PREFIX)$(ASTLIBDIR)
endif
ifeq ($(strip $(DOCDIR)),)
	DOCUMENTATION_DIR:=$(INSTALL_PREFIX)/usr/share/asterisk/documentation/thirdparty
else
	DOCUMENTATION_DIR:=$(INSTALL_PREFIX)$(DOCDIR)
endif
INSTALL = install
ASTETCDIR = $(INSTALL_PREFIX)/etc/asterisk
SAMPLENAME = stasis_amqp.conf.sample
CONFNAME = $(basename $(SAMPLENAME))

ARI_OBJECTS = res_ari_amqp.o resource_amqp.o
STASIS_OBJECTS = res_stasis_amqp.o
TARGET = res_stasis_amqp.so res_ari_amqp.so
CFLAGS += -I../asterisk-amqp
CFLAGS += -DHAVE_STDINT_H=1
CFLAGS += -Wall -Wextra -Wno-unused-parameter -Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations -Winit-self -Wmissing-format-attribute \
          -Wformat=2 -g -fPIC -D_GNU_SOURCE -D'AST_MODULE="res_stasis_amqp"' -D'AST_MODULE_SELF_SYM=__internal_res_stasis_amqp_self'
LDFLAGS = -Wall -shared

.PHONY: install clean

all: $(TARGET)

%.o: %.c $(HEADERS)
	$(CC) -c $(CFLAGS) -o $@ $<

install: all
	mkdir -p $(DESTDIR)$(MODULES_DIR)
	mkdir -p $(DESTDIR)$(DOCUMENTATION_DIR)
	install -m 644 res_stasis_amqp.so $(DESTDIR)$(MODULES_DIR)
	install -m 644 res_ari_amqp.so $(DESTDIR)$(MODULES_DIR)
	install -m 644 documentation/* $(DESTDIR)$(DOCUMENTATION_DIR)
	@echo " +-------- res_stasis_amqp installed --------+"
	@echo " +                                           +"
	@echo " + res_amqp has successfully been installed  +"
	@echo " + If you would like to install the sample   +"
	@echo " + configuration file run:                   +"
	@echo " +                                           +"
	@echo " +              make samples                 +"
	@echo " +-------------------------------------------+"

clean:
	rm -f $(ARI_OBJECTS)
	rm -f $(STASIS_OBJECTS)
	rm -f $(TARGET)

samples:
	$(INSTALL) -m 644 $(SAMPLENAME) $(DESTDIR)$(ASTETCDIR)/$(CONFNAME)
	@echo " ------- res_stasis_amqp config installed ---------"

res_ari_amqp.so: $(ARI_OBJECTS)
	$(CC) $(LDFLAGS)  -o $@ $^ $(LIBS)

res_stasis_amqp.so: $(STASIS_OBJECTS)
	$(CC) $(LDFLAGS)  -o $@ $^ $(LIBS)
