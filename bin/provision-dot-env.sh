#!/usr/bin/env bash

PARENT_PATH=$(dirname "${BASH_SOURCE[0]}")
DOT_ENV_PATH="$PARENT_PATH/../.env"

cp -n "$PARENT_PATH/../.env.docker.example" "$DOT_ENV_PATH" | true

declare -a VARS=("PLATFORM_EMAIL_HOST_USER"
  "PLATFORM_EMAIL_HOST_PASSWORD"
  "PLATFORM_TWILIO_ACCOUNT_SID"
  "PLATFORM_TWILIO_AUTH_TOKEN"
  "PLATFORM_TWILIO_SMS_FROM")

echo "Provisioning .env file with variables from environment (if defined): [${VARS[*]}] ..."

for var in "${VARS[@]}"
do
  if [ -n "${var}" ]; then
    echo "--> Updating $var"
    sed -i "/^$var=/c\\$var=${!var}" "$DOT_ENV_PATH"
  fi
done
