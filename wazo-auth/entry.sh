#!/bin/sh

until ./bin/wazo-auth-init-db --pg_db_uri postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@postgresql/$POSTGRES_DB --auth_db_uri postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@postgresql/$POSTGRES_DB; do
    sleep 1
done

cd /usr/src/wazo-auth && alembic -c alembic.ini upgrade head

wazo-auth -d

sleep 5

if [ ! -f /root/.config/wazo-auth-cli/050-credentials.yml ]; then
    wazo-auth-bootstrap complete
fi

CLI_USERNAME=$( cat /root/.config/wazo-auth-cli/050-credentials.yml | grep username | cut -d ':' -f 2 | tr -d ' ')
CLI_PASSWORD=$( cat /root/.config/wazo-auth-cli/050-credentials.yml | grep password | cut -d ':' -f 2 | tr -d ' ')
CLI_BACKEND=$( cat /root/.config/wazo-auth-cli/050-credentials.yml | grep backend | cut -d ':' -f 2 | tr -d ' ')

TOKEN=$(curl -s -X POST -H 'Content-Type: application/json' -u "$CLI_USERNAME:$CLI_PASSWORD" "http://localhost:9497/0.1/token" -d "{\"backend\": \"$CLI_BACKEND\"}" | jq -r .data.token)

USER_UUID=$( curl -s -X POST "http://localhost:9497/0.1/users" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"password\": \"$PASSWORD\", \"purpose\": \"user\", \"username\": \"$USERNAME\", \"uuid\": \"$UUID\"}" -H "X-Auth-Token: $TOKEN" | jq -r .uuid )

# set ACL for application bus event
ACL_UUID=$( curl -s -X POST "http://localhost:9497/0.1/policies"  -H  "accept: application/json" -H  "Content-Type: application/json" -d "{ \"acl_templates\": [\"events.applications.#\"], \"description\": \"application events\", \"name\": \"application_events\" }"  -H "X-Auth-Token: $TOKEN" | jq -r .uuid )
curl -X PUT "http://localhost:9497/0.1/users/$USER_UUID/policies/$ACL_UUID" -H  "accept: application/json" -H  "Content-Type: application/json" -d "" -H "X-Auth-Token: $TOKEN"

while true; do
    sleep 1
done