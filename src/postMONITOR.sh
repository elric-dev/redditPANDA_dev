#!/bin/bash
until ./postCRAWLER.py $1; do
    echo "The postCRAWLER crashed with exit code $?. Restarting in 10 minutes..." > &2
    sleep 600
done
