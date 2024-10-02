#!/bin/bash

service supervisor start

apache2ctl -D FOREGROUND
