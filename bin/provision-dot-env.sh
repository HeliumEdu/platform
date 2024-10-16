#!/usr/bin/env bash

PARENT_PATH=$(dirname "${BASH_SOURCE[0]}")
DOT_ENV_PATH="$PARENT_PATH/../.env"

make -C "$PARENT_PATH/.." docker-env

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
    # Prefer gsed, if it's installed (required on Mac)
    which gsed
    if [ $? -eq 0 ]; then
      sed_cmd="gsed"
    else
      sed_cmd="sed"
    fi

    "${sed_cmd[@]}" -i "/^$var=/c\\$var=${!var}" "$DOT_ENV_PATH"
  fi
done
