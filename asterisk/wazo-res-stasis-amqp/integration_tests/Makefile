test-setup:
	docker pull debian:buster
	docker pull wazopbx/wait
	docker build --no-cache -t asterisk_amqp ..
	docker pull rabbitmq

test:
	py.test -x suite
