import wazo_websocketd_client
import wazo_auth_client

from wazo_applicationd_client import Configuration  # type: ignore
from wazo_applicationd_client import ApiClient
from wazo_applicationd_client import ApiException
from wazo_applicationd_client.api import ApplicationApi

configuration = Configuration()
configuration.host = "http://localhost:8000"

api_client = ApiClient(configuration)
api = ApplicationApi(api_client)

c = wazo_auth_client.Client('localhost', username='admin', password='secret', https=False)

# Tokens
reply = c.token.new('wazo_user', expiration=3600, session_type='mobile') 
print(reply)
c = wazo_websocketd_client.Client("localhost", port=9502, token=reply["token"], verify_certificate=False, wss=False)

def callback(data):
    print("Coucou")
    print(data)
    call_id = data["call"]["id"]
    app_uuid = data["application_uuid"]
    print(call_id)
    context_token = data["context_token"]

    api.answer_call10_applications_app_uuid_calls_call_id_answer_put(app_uuid, call_id, x_context_token=context_token)

c.on('application_user_outgoing_call_created', callback)

c.run()
