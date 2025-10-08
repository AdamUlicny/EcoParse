#! /usr/bin/bash

sudo docker buildx build -t ecoparse-app .
sudo docker run -p 8501:8501 -p 4040:4040 ecoparse-app
