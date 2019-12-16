import ari


def on_event(channel, event):
	print("%s : %s" % (channel, event))


def on_registered():
	print("Application registered")
	

client = ari.connect('http://localhost:8888/', 'wazo', 'wazo')
client.on_channel_event('StasisStart', on_event)
client.on_application_registered('hello', on_registered)
client.run(apps="hello")
