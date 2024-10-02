#!/bin/bash

supervisord -n & apache2ctl -D FOREGROUND