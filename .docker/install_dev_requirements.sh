#!/bin/bash -x

if [[ $ENV = "DEV" ]]; then
	pip install -r requirements.dev.txt
fi