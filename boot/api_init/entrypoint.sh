#!/bin/bash

cd ./workspace

MODULE="${API_VM_PROJECT_APP}"

uvicorn $MODULE --host 0.0.0.0 --port 8000