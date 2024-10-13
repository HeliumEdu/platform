#!/usr/bin/env bash

if [ "$PLATFORM_BEAT_MODE" == "True" ] && [ "$PLATFORM_BEAT_AND_WORKER_MODE" == "True" ]
then
  echo "Only one of 'PLATFORM_BEAT_MODE' or 'PLATFORM_BEAT_AND_WORKER_MODE' can be set to 'True'"
  exit 1
fi

if [ "$PLATFORM_BEAT_MODE" == "True" ]
then
  echo "PLATFORM_BEAT_MODE set, enabling supervisor as a Beat scheduler only (only ever run one Beat scheduler in the fleet)"
  mv /etc/supervisor/conf.d/celerybeat.conf.disabled /etc/supervisor/conf.d/celerybeat.conf 2>/dev/null; true
  mv /etc/supervisor/conf.d/celeryworker.conf /etc/supervisor/conf.d/celeryworker.conf.disabled 2>/dev/null; true
elif [ "$PLATFORM_BEAT_AND_WORKER_MODE" == "True" ]
then
  echo "PLATFORM_BEAT_AND_WORKER_MODE set, enabling supervisor as both Beat scheduler and Worker (usually only done in development)"
  mv /etc/supervisor/conf.d/celerybeat.conf.disabled /etc/supervisor/conf.d/celerybeat.conf 2>/dev/null; true
  mv /etc/supervisor/conf.d/celeryworker.conf.disabled /etc/supervisor/conf.d/celeryworker.conf 2>/dev/null; true
else
  mv /etc/supervisor/conf.d/celerybeat.conf /etc/supervisor/conf.d/celerybeat.conf.disabled 2>/dev/null; true
  mv /etc/supervisor/conf.d/celeryworker.conf.disabled /etc/supervisor/conf.d/celeryworker.conf 2>/dev/null; true
fi

supervisord -c /etc/supervisor/supervisord.conf -n
