#!/bin/bash

this="$(realpath ${0})"
pkgtop="$(realpath ${this%/*}/../../)"
tmpworkdir="${TMPWORKDIR:-${TMPDIR:-/tmp}/enc_ds_test}"

export PYTHONPATH="${pkgtop}:${tmpworkdir}/lib/python/site-package:${PYTHONPATH}"

prefx="${tmpworkdir}/var/run/top"
storagename="TestEncipherdDataStorage"
masterkeyphrase='KernelWaniWaniPanic'
keyid='testenckey@localhost.localdomain'
keybits=4096
passphrase='CheckCheckCheck'

data_formats="json yaml ini toml"

for fmt in ${data_formats}; do
    echo "Check encryption and decyption : ${fmt}"
    rm "${prefx}/var/run/enc-ds/data/testdata.${fmt}"

    "${PYTHON:-python3}" "${pkgtop}/bin/enciphered_datastorage.py" \
            --prefix "${prefx}" \
            --storage-name "${storagename}" \
            --master-key-phrase "${masterkeyphrase}" \
            --key-id "${keyid}" \
            --key-bits "${keybits}" \
            --passphrase "${passphrase}" \
            --serialize-format "${fmt}" \
            -e \
            -D 2\
            -o testdata.json \
            -A DataCategory \
            -k DataSetName \
            -K DataKey1 \
            Data0 Data1 "$@"
    
    "${PYTHON:-python3}" "${pkgtop}/bin/enciphered_datastorage.py" \
            --prefix "${prefx}" \
            --storage-name "${storagename}" \
            --master-key-phrase "${masterkeyphrase}" \
            --key-id "${keyid}" \
            --key-bits "${keybits}" \
            --passphrase "${passphrase}" \
            --serialize-format "${fmt}" \
            -e \
            -a -D 2 \
            -r testdata.json \
            -o testdata.json \
            -A DataCategory \
            -k DataSetName \
            -K DataKey2 \
            Data3 Data4 "$@"
    
    "${PYTHON:-python3}" "${pkgtop}/bin/enciphered_datastorage.py" \
            --prefix "${prefx}" \
            --storage-name "${storagename}" \
            --master-key-phrase "${masterkeyphrase}" \
            --key-id "${keyid}" \
            --key-bits "${keybits}" \
            --passphrase "${passphrase}" \
            --serialize-format "${fmt}" \
            -d \
            -r testdata.json \
            -A DataCategory \
            "$@"
    ls -l "${prefx}/var/run/enc-ds/data/testdata.${fmt}"
    [ -f "${prefx}/var/run/enc-ds/data/testdata.${fmt}" ] && echo "Data file created" || { echo "Error" ; exit ; }
done

