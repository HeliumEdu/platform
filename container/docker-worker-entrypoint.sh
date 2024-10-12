#!/usr/bin/env bash

if [ "$PLATFORM_WORKER_BEAT_MODE" == "True" ]
then
  echo "PLATFORM_WORKER_BEAT_MODE set, starting supervisor as a beat worker (only one should ever be running in the fleet)"
  mv /etc/supervisor/conf.d/celerybeat.conf.disabled /etc/supervisor/conf.d/celerybeat.conf 2>/dev/null; true
  if [ "$PLATFORM_BEAT_AND_WORKER_ENABLED" == "True" ]
  then
    echo "PLATFORM_BEAT_AND_WORKER_ENABLED set, leaving worker enabled"
    mv /etc/supervisor/conf.d/celeryworker.conf.disabled /etc/supervisor/conf.d/celeryworker.conf 2>/dev/null; true
  else
    mv /etc/supervisor/conf.d/celeryworker.conf /etc/supervisor/conf.d/celeryworker.conf.disabled 2>/dev/null; true
  fi
else
  mv /etc/supervisor/conf.d/celerybeat.conf /etc/supervisor/conf.d/celerybeat.conf.disabled 2>/dev/null; true
fi


supervisord -c /etc/supervisor/supervisord.conf -n
