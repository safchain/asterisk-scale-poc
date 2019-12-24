#
# Makefile for Asterisk Consul discovery resource
#
# * Copyright (C) 2019, The Wazo Authors (see the AUTHORS file)
#
# This program is free software, distributed under the terms of
# the GNU General Public License Version 3. See the COPYING file
# at the top of the source tree.
#

ASTINCDIR = $(INSTALL_PREFIX)/usr/include/asterisk
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
SAMPLENAME = res_consul_discovery.conf.sample
CONFNAME = $(basename $(SAMPLENAME))

TARGET = res_consul_discovery.so
OBJECTS = res_consul_discovery.o
CFLAGS += -I.
CFLAGS += -DHAVE_STDINT_H=1
CFLAGS += -Wall -Wextra -Wno-unused-parameter -Wstrict-prototypes -Wmissing-declarations -Winit-self -Wmissing-format-attribute \
          -Wformat=2 -g -fPIC -D_GNU_SOURCE -D'AST_MODULE="res_consul_discovery"' -D'AST_MODULE_SELF_SYM=__internal_res_consul_discovery_self'
LIBS += -lcurl
LDFLAGS = -Wall -shared

.PHONY: install clean

$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@ $(LIBS)

%.o: %.c $(HEADERS)
	$(CC) -c $(CFLAGS) -o $@ $<

install: $(TARGET)
	mkdir -p $(DESTDIR)$(MODULES_DIR)
	mkdir -p $(DESTDIR)$(DOCUMENTATION_DIR)
	mkdir -p $(DESTDIR)$(ASTINCDIR)
	install -m 755 $(TARGET) $(DESTDIR)$(MODULES_DIR)
	@echo " +----------- res_consul_discovery installed ------------+"
	@echo " +                                                       +"
	@echo " + res_consul_discovery has successfully been installed  +"
	@echo " + If you would like to install the sample configuration +"
	@echo " + file run:                                             +"
	@echo " +                                                       +"
	@echo " +              make samples                             +"
	@echo " +-------------------------------------------------------+"

clean:
	rm -f $(OBJECTS)
	rm -f $(TARGET)

samples:
	$(INSTALL) -m 644 $(SAMPLENAME) $(DESTDIR)$(ASTETCDIR)/$(CONFNAME)
	@echo " ------- res_consul_discovery config installed ---------"
