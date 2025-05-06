# enc-ds

enc-ds (Enciphered-Data-Storage): Utility for simple encrypted data storage using RSA signatures via `ssh-agent`

`enc_ds` provides the AES-GCM encryption/decryption with the key derivation with RSA signature using the private key fetched from `ssh-agent`. 

With this method, as long as you use an RSA private key with a passphrase, all of the information needed for decryption does not need to be stored on the file system. On the other hand, if you register your RSA private key in `ssh-agent`, you can decrypt using it without using the passphrase of the RSA private key each time. (See "share/materials/cipher_diagram_0.png" and "share/materials/cipher_diagram_1.png" for the diagrams for encryption/decryption)

This module uses the `sshkeyring` module for RSA key management. It also supports RSA key generation at first startup, startup when `ssh-agent` is not up, registration of keys to `ssh-agent`, etc.

This module supports dict and list type data in a multi-layered tree structure. The `enc_ds.DataTree` class can contain data of multi-layered tree structure and provides reading and writing of these data in json, yaml, ini, and toml. In addition, the `enc_ds.EncDataStorage` class provides encryption/decryption for the data of the encapsulated `enc_ds.DataTree` class. In addition, `enciphered_datastorage.py` is a command line tool that encrypts and displays the given data, and also provides the ability to encrypt/decrypt and display simple json,yaml,ini,toml files.

## Requirement

  - cryptography
  - paramiko
  - PyNaCl
  - PyYAML
  - toml
  - pkgstruct
  - sshkeyring
  - argparse_extd

## Usage

class `enc_ds.DataTree` provides the data storage with tree-structure;

```python:example
base_data = {'Level1a': {'Level2a': [ {'url': 0}, {'port': 2} ]},
             'Level1b': {'Level2b': [ {'url': 1}, {'port': 2} ]}}

dtr = enc_ds.DataTree(base_obj=base_data, identifier='DataName')

# Contents can be accessed by [key] where key is the tuple for the index for each layer.
dtr[('Level1a', 'Level2a', 0, 'url',      )] = 'https://www.yaaa.co.jp' # Data Update
dtr[('Level1a', 'Level2a', 0, 'port',     )] = 433                      # Data Update
dtr[('Level1a', 'Level2a', 0, 'user',     )] = 'person_a'               # Data add
dtr[('Level1a', 'Level2a', 1, 'url',      )] = 'https://www.ybbb.co.jp' # Data add
dtr[('Level1a', 'Level2a', 1, 'port',     )] = 433                      # Data add
dtr[('Level1a', 'Level2a', 1, 'user',     )] = 'person_b'               # Data add

# Output to serialized data/file (yaml,json,ini,toml)

contents = dtr.serialize(output_format='json',...)
dtr.save_serialized(file_path: str,...)

# Input from serialized data/file (yaml,json,ini,toml)

dtr.load_deserialized(content:str, update=True, input_format='json', getall=True)
dtr.read_serialized(file_path: str, update=True, input_format='json', getall=True)
```

class `enc_ds.EncDataStorage` provides the SSH-KEY interface (moudle `sshkeyring`), and has the `DataTree` member for data storage.


```python:example
encds = enc_ds.EncDataStorage(storage_name:str,
                              storage_masterkey:str,
                              data_identifier,
                              key_id:str,
                              key_file_basename)
encds.io_format   = 'json'
encds.input_path  = "data_input_path"
encds.output_path = "data_output_path"

# Setup SSH Key Interface
encds.setup_sshkeyinfo()

base_obj = { ... } # Initial Object

encds.set_datatree(identifier='DataCategoryName', base_obj=base_obj)

# Data can be manipulated as follows
encds.datatree[('system_info', 'date')] = datetime.datetime.now().ctime()


# Read data from file and Decipher the encripted data
encds.read_datatree(update=True, getall=True,
                    decipher=False, decipher_entire_data=True)
print(encds.datatree) # Access to internal Data

# Enciper the data
encds.decipher(category="DataCategoryName", entire_data=True)
print(encds.datatree) # Print the deciphered data

# Save Encipered data
encds.save_datatree(encipher=False, bulk=True, .... )

# Deciper the data
encds.decipher(category="DataCategoryName", entire_data=True)
print(encds.datatree) # Print the deciphered data

# class enc_ds.EncipherStorageUnit provides more simple method.
encds.set_cipher_unit()
#
raw_data = { .... }
# encrypting object
encrypted_data = encds.cipher_unit.encipher(raw_data=raw_data)
# decrypting object
decrypted_data = encds.cipher_unit.decipher(enc_object=encrypted_data)
```

## Examples

Typical usage of `enc_ds` module can be see in the source of `enciphered_datastorage.py`. 
The usage of the `enciphered_datastorage.py` as the utility CLI script is as follows.

```
usage: enciphered_datastorage.py [-p PREFIX] [-N STORAGE_NAME]
                                 [-c DEFAULT_CONFIG] [-F {ini,yaml,json,toml}]
                                 [-h] [-C CONFIG] [-S [SAVE_CONFIG]]
                                 [--save-config-default] [-v] [-q]
                                 [-M MASTER_KEY_PHRASE] [-J KDF_ITERATIONS]
                                 [-H] [-i KEY_ID] [-b KEY_BITS]
                                 [-B KEYFILE_BASENAME] [-U] [-P PASSPHRASE]
                                 [-L] [-W] [-I] [-m PASSPHRASE_LENGTH_MIN]
                                 [-f {json,JSON,yaml,yml,YAML,YML,ini,INI,toml,TOML}]
                                 [-n ENCIPHER_DATA_NAME] [-E] [-r INPUT_FILE]
                                 [-o OUTPUT_FILE] [-x] [-y] [-z]
                                 [-Z [{bz2,gz,xz}]] [-A CATEGORY_NAME]
                                 [-k KEY_OF_DATA_SET] [-D ENCIPHER_DEPTH] [-e]
                                 [-a] [-d] [-K KEY_OF_DATA]
                                 [argv ...]

positional arguments:
  argv                  Text data to be enciphered

options:
  -p, --prefix PREFIX   Directory Prefix
  -N, --storage-name STORAGE_NAME
                        Storage name
  -c, --default-config DEFAULT_CONFIG
                        Default config filename (Default:
                        ${storage_name}+".config.yaml" like
                        "enciphered_datastorage.config.yaml")
  -F, --config-format {ini,yaml,json,toml}
                        conf. file format
  -h, --help            show this help message and exit
  -C, --config CONFIG   path of the configuration file to be loaded
  -S, --save-config [SAVE_CONFIG]
                        path of the configuration file to be saved
  --save-config-default
                        path of the configuration file to be saved(Use
                        default: ....... )
  -v, --verbose         show verbose messages
  -q, --quiet           supress verbose messages
  -M, --master-key-phrase MASTER_KEY_PHRASE
                        Master Key Phrase of storage
  -J, --kdf-iterations KDF_ITERATIONS
                        Iterations in Key Derivation function
  -H, --class-help      Show help for enc_ds classes
  -i, --key-id KEY_ID   Specify key id: Default is .............
  -b, --key-bits KEY_BITS
                        Specity Key length
  -B, --keyfile-basename KEYFILE_BASENAME
                        Key file basename
  -U, --use-openssh-keys
                        Use openssh keys (in False)
  -P, --passphrase PASSPHRASE
                        SSH key passphrase (common)
  -L, --disuse-ssh-agent
                        run without ssh-agent
  -W, --allow-keyfile-overwrite
                        Allow overwrite keyfile if already exists
  -I, --invoke-ssh-agent
                        invoke ssh-agent if no ssh-agent is running
  -m, --passphrase-length-min PASSPHRASE_LENGTH_MIN
                        Minimum length of key passphrase
  -f, --serialize-format {json,JSON,yaml,yml,YAML,YML,ini,INI,toml,TOML}
                        Serialization Format
  -n, --encipher-data-name ENCIPHER_DATA_NAME
                        Encipherd storage name
  -E, --encipher-data-dict-key
                        Encrypt key of dict-type data
  -r, --input-file INPUT_FILE
                        Input file name
  -o, --output-file OUTPUT_FILE
                        Output file name
  -x, --input-from-default-path
                        Input from default data file
  -y, --output-to-default-path
                        Input from default data file
  -z, --io-with-config-file
                        I/O to config file
  -Z, --compress [{bz2,gz,xz}]
                        Compress output
  -A, --category-name CATEGORY_NAME
                        Data Category Name
  -k, --key-of-data-set KEY_OF_DATA_SET
                        Data set Name
  -D, --encipher-depth ENCIPHER_DEPTH
                        depth of node to be enciphered(default=1)
  -e, --encode-mode     Encipher mode
  -a, --append-data     Append data in encipher mode
  -d, --decode-mode     Decipher mode
  -K, --key-of-data KEY_OF_DATA
                        Data Category Name
```

The examples at the command line is as follows.

- Encryption

```
prefix="${home}/..../somewhere"
storagename="TestEncipherdDataStorage"
masterkeyphrase='KernelWaniWaniPanic'
keyid='testenckey@localhost.localdomain'
keybits=4096
passphrase='CheckCheckCheck'

fmt="json" #  "yaml" "ini" "toml"

"${PYTHON:-python3}" "bin/enciphered_datastorage.py" \
    --prefix "${prefix}" \
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
    Data0 Data1

"${PYTHON:-python3}" "bin/enciphered_datastorage.py" \
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
    Data3 Data4
```

- Decryption
```
prefix="${home}/..../somewhere"
storagename="TestEncipherdDataStorage"
masterkeyphrase='KernelWaniWaniPanic'
keyid='testenckey@localhost.localdomain'
keybits=4096
passphrase='CheckCheckCheck'

"${PYTHON:-python3}" "bin/enciphered_datastorage.py" \
            --prefix "${prefix}" \
            --storage-name "${storagename}" \
            --master-key-phrase "${masterkeyphrase}" \
            --key-id "${keyid}" \
            --key-bits "${keybits}" \
            --passphrase "${passphrase}" \
            --serialize-format "${fmt}" \
            -d \
            -r testdata.json \
            -A DataCategory
```


## Author
    Nanigashi Uji (53845049+nanigashi-uji@users.noreply.github.com)
    Nanigashi Uji (4423013-nanigashi_uji@users.noreply.gitlab.com)
