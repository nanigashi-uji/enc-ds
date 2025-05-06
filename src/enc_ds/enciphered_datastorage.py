#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import datetime
import string
import secrets
import pydoc
#import pytz
#import tzlocal

import inspect

import base64
import copy
import pathlib

import pkgstruct
import argparse_extd
import sshkeyring

import enc_ds

def main():

    # Guess the location of data storage
    this_name                 = sys.argv[0].removesuffix('.py')
    pkg_info                  = pkgstruct.PkgStruct(script_path=this_name)
    storage_name              = pkg_info.script_basename
    serialized_format_default = 'yaml'
    config_ext_default        = '.config'+'.'+serialized_format_default
    config_default            = storage_name+config_ext_default
    master_key_phrase         = storage_name + 'AburaKataBura'
    kdf_iterations            = 1000000
    
    # Re-set the location of data storage if it is specified by command line option
    argprsr = argparse_extd.ArgumentParserExtd(add_help=False)
    argprsr.add_argument('-p', '--prefix', type=str, help='Directory Prefix')
    argprsr.add_argument('-N', '--storage-name', type=str, default=storage_name, help='Storage name')
    argprsr.add_argument('-c', '--default-config', type=str, default=None, help=('Default config filename (Default: ${storage_name}+"%s" like "%s")'
                                                                                 % (config_ext_default, config_default)))
    argprsr.add_argument('-F', '--config-format', type=str,
                         choices=argparse_extd.ArgumentParserExtd.CONFIG_FORMAT,
                         default=argparse_extd.ArgumentParserExtd.path_format_extsplit(config_ext_default)[1],
                         help='conf. file format')
    
    opts,remains=argprsr.parse_known_args()
    pkg_info=pkgstruct.PkgStruct(prefix=opts.prefix, script_path=this_name)
    if isinstance(opts.storage_name,str) and opts.storage_name:
        storage_name = opts.storage_name

    if isinstance(opts.default_config,str) and opts.default_config:
        config_default = opts.default_config
    else:
        if isinstance(opts.config_format, str) and opts.config_format:
            config_ext_default = '.config'+'.'+opts.config_format
        config_default = storage_name + config_ext_default

    #pkg_default_config=pkg_info.concat_path('pkg_runstatedir', 'config', config_default)
    pkg_default_config=pkg_info.complement('pkg_runstatedir', 'config', config_default)

    # Read configuration file as default setting
    argprsr.load_config(pkg_default_config)

    cfg_bn, cfg_fmt, cfg_cmp = argparse_extd.ArgumentParserExtd.path_format_extsplit(pkg_default_config)

    # Set optional arguments
    argprsr.add_argument_help()

    argprsr.add_argument_config()
    argprsr.add_argument_save_config(default_path=pkg_default_config)
    argprsr.add_argument_verbose()
    argprsr.add_argument_quiet(dest='verbose')
    argprsr.add_argument('-M', '--master-key-phrase', type=str, default=master_key_phrase, help='Master Key Phrase of storage')
    argprsr.add_argument('-J', '--kdf-iterations', type=int, default=kdf_iterations, help='Iterations in Key Derivation function')
    argprsr.add_argument('-H', '--class-help', action='store_true',
                         help='Show help for enc_ds classes')

    argprsr.add_argument('-i', '--key-id',   default=None, 
                         help=('Specify key id: Default is %s' % ( sshkeyring.SSHKeyUtil.Default_Key_Id(),) ))
    argprsr.add_argument('-b', '--key-bits', type=int, default=None, help='Specity Key length')
    argprsr.add_argument('-B', '--keyfile-basename', default=None, help='Key file basename')
    argprsr.add_argument('-U', '--use-openssh-keys', default=None, action='store_true',
                         help=( 'Use openssh keys (in %s)' % (sshkeyring.SSHKeyUtil.SEEK_OPENSSH_KEYDIR_DEFAULT,)))
    argprsr.add_argument('-P', '--passphrase', type=str, default=None, help='SSH key passphrase (common)')
    argprsr.add_argument('-L', '--disuse-ssh-agent', action='store_true', help='run without ssh-agent')

    argprsr.add_argument('-W', '--allow-keyfile-overwrite', action='store_true', help='Allow overwrite keyfile if already exists')
    argprsr.add_argument('-I', '--invoke-ssh-agent', action='store_true', help='invoke ssh-agent if no ssh-agent is running')
    argprsr.add_argument('-m', '--passphrase-length-min', type=int, default=8, help='Minimum length of key passphrase')

    argprsr.add_argument('-f', '--serialize-format', type=str, default=serialized_format_default,
                         choices=enc_ds.DataTree.SERIALIZE_FORMATS, help='Serialization Format')
    argprsr.add_argument('-n', '--encipher-data-name', type=str, default='', help='Encipherd storage name')
    argprsr.add_argument('-E', '--encipher-data-dict-key', action='store_true', help='Encrypt key of dict-type data')

    argprsr.add_argument('-r', '--input-file',   type=str, help='Input file name')
    argprsr.add_argument('-o', '--output-file',  type=str, help='Output file name')
    argprsr.add_argument('-x', '--input-from-default-path', action='store_true',  help='Input from default data file')
    argprsr.add_argument('-y', '--output-to-default-path',  action='store_true',  help='Input from default data file')
    argprsr.add_argument('-z', '--io-with-config-file',     action='store_true',  help='I/O to config file')
    argprsr.add_argument('-Z', '--compress', type=str, nargs='?', const='bz2',
                         choices=[x[1:] for x in enc_ds.DataTree.COMPRESS_EXT], help='Compress output')

    argprsr.add_argument('-A', '--category-name',   type=str, help='Data Category Name')
    argprsr.add_argument('-k', '--key-of-data-set', type=str, help='Data set Name')
    argprsr.add_argument('-D', '--encipher-depth',  type=int, nargs=None, default=1, 
                        help='depth of node to be enciphered(default=1)')

    argprsr.add_argument('-e', '--encode-mode',  action='store_true', help='Encipher mode')
    argprsr.add_argument('-a', '--append-data',  action='store_true', help='Append data in encipher mode')

    argprsr.add_argument('-d', '--decode-mode',  action='store_true', help='Decipher mode')
    argprsr.add_argument('-K', '--key-of-data',     type=str, help='Data Category Name')

    argprsr.add_argument('argv', nargs='*', help='Text data to be enciphered')

    argprsr.append_write_config_exclude(('--prefix', '--default-config',
                                         '--verbose', '--save-config', 'argv'))

    argprsr.append_write_config_exclude(('--allow-keyfile-overwrite',
                                         '--encipher-data-name',
                                         '--encipher-data-dict-key',
                                         '--input-from-default-path',
                                         '--output-to-default-path',
                                         '--io-with-config-file',
                                         '--compress',
                                         '--category-name',
                                         '--key-of-data-set',
                                         '--encipher-depth',
                                         '--encode-mode',
                                         '--append-data',
                                         '--decode-mode',
                                         '--serialize-format',
                                         '--key-of-data'))

    opts = argprsr.parse_args(action_help=True)

    if argprsr.args.class_help:
        pydoc.help = pydoc.Helper(output=sys.stdout)
        help(enc_ds.EncipherStorageUnit)
        help(enc_ds.EncStoreUnit)
        help(enc_ds.EncStoreUnit)
        help(enc_ds.DataTreeBase)
        help(enc_ds.DataTree)
        help(enc_ds.CipherDataTree)
        help(enc_ds.EncDataStorage)
        sys.exit()

    if argprsr.args.verbose:
        sys.stderr.write("Prefix              : %s\n" % (pkg_info.prefix, ) )
        sys.stderr.write("Default config      : %s\n" % (argprsr.args.default_config, ) )
        sys.stderr.write("Default config path : %s\n" % (pkg_default_config, ) )

    if argprsr.args.io_with_config_file:
        serialize_format = argprsr.args.config_format
    else:
        serialize_format = argprsr.args.serialize_format
    
    io_compress      = argprsr.args.compress

    data_path_default = pkg_info.complement('pkg_runstatedir','data', 
                                            filename=enc_ds.EncDataStorage.set_path_ext(storage_name+'_data',
                                                                                        serialize_format, io_compress))
    if argprsr.args.verbose:
        sys.stderr.write("Default data path   : %s\n" % (data_path_default, ) )

    if argprsr.args.io_with_config_file:
        if ( argprsr.args.encode_mode and
             argprsr.args.category_name is None and
             argprsr.args.key_of_data is None):
            sys.stderr.write("[%s.%s:%d] Error: 'io_with_config_file' is specified with neither '--cagegory-name' nor '--key-of-data'.\n"
                             % (__name__, inspect.currentframe().f_code.co_name, inspect.currentframe().f_lineno))
            sys.exit()


        serialize_format,io_compress = enc_ds.EncDataStorage.guess_format(pkg_default_config)
        data_input_path  = pkg_default_config
        data_output_path = pkg_default_config
    else:
        if ( (not argprsr.args.input_from_default_path) and 
             isinstance(argprsr.args.input_file,str) and argprsr.args.input_file ):
            data_input_path = pkg_info.complement('pkg_runstatedir','data', argprsr.args.input_file)
        else:
            data_input_path = data_path_default

        if ( (not argprsr.args.output_to_default_path) and 
             isinstance(argprsr.args.output_file,str) and argprsr.args.output_file ):
            data_output_path = pkg_info.complement('pkg_runstatedir','data', argprsr.args.output_file)
        else:
            data_output_path = data_path_default

    use_key_id = argprsr.args.key_id   if isinstance(argprsr.args.key_id, str) and argprsr.args.key_id   else sshkeyring.SSHKeyRing.Default_Key_Id()
    key_bits   = argprsr.args.key_bits if isinstance(argprsr.args.key_bits,int) else 4096
    category    = argprsr.args.category_name

    encds = enc_ds.EncDataStorage(storage_name=storage_name, 
                                  storage_masterkey=master_key_phrase,
                                  data_identifier=category,
                                  sshkey_passphrase=argprsr.args.passphrase,
                                  min_passphrase_length=argprsr.args.passphrase_length_min,
                                  key_id=use_key_id, key_bits=key_bits,
                                  key_file_basename=argprsr.args.keyfile_basename,
                                  keypath_prefix=pkg_info.prefix,
                                  keypath_private=None, keypath_public=None,
                                  use_openssh_keys=argprsr.args.use_openssh_keys,
                                  allow_keyfile_overwrite=argprsr.args.allow_keyfile_overwrite,
                                  use_ssh_agent=(not argprsr.args.disuse_ssh_agent),
                                  invoke_ssh_agent=argprsr.args.invoke_ssh_agent,
                                  register_agent=(not argprsr.args.disuse_ssh_agent))

    encds.io_format   = serialize_format
    encds.in_format   = serialize_format
    encds.out_format  = serialize_format
    encds.input_path  = data_input_path
    encds.output_path = data_output_path

    if argprsr.args.verbose:
        sys.stderr.write("Enciphered  Input       : %s\n" % (encds.input_path,))
        sys.stderr.write("Enciphered  Output      : %s\n" % (encds.output_path,))

    encds.setup_sshkeyinfo(verbose=argprsr.args.verbose)

    if argprsr.args.decode_mode:

        base_obj = {}

        if argprsr.args.io_with_config_file:
            base_obj.update( { k : v for k,v in argprsr.args.to_dict().items() 
                               if not k in argprsr.write_config_exclude_default })
            encds.set_cipher_unit(encipher_data_dict_key=argprsr.args.encipher_data_dict_key)
            base_obj = encds.cipher_unit.decipher(enc_object=base_obj, verbose=argprsr.args.verbose)

        encds.set_datatree(identifier=category, base_obj=base_obj,
                           encipher_data_dict_key=argprsr.args.encipher_data_dict_key)

        if ( (not argprsr.args.io_with_config_file) and 
             ( isinstance(data_input_path, str) and data_input_path ) ):
            encds.read_datatree(update=True, identifier=None, getall=True, index=None,
                                decipher=False, decipher_entire_data=True, verbose=argprsr.args.verbose)
            
        if argprsr.args.verbose:
            sys.stdout.write("----- Input ---------------------------------------------------\n")
            print(encds.datatree)

        if argprsr.args.verbose:
            sys.stdout.write("----- Deciphered ----------------------------------------------\n")

        encds.decipher(category, entire_data=True, verbose=argprsr.args.verbose)
        print(encds.datatree)

        # sys.stdout.write("----- Re-Enciphered -------------------------------------------\n")
        # encds.encipher(category, entire_data=False, verbose=argprsr.args.verbose)
        # print(encds.datatree)

        if argprsr.args.verbose:
            sys.stdout.write("---------------------------------------------------------------\n")

        if argprsr.args.save_config:
            argprsr.save_config_action()

        return 

    elif argprsr.args.encode_mode:

        base_obj = {'system_info' : {'date':     datetime.datetime.now().ctime(),
                                     'platform': sys.platform,
                                     'version':  sys.version}}

        encipher_depth = int(argprsr.args.encipher_depth)
        data_key = tuple([ x for x in [ argprsr.args.category_name,
                                        argprsr.args.key_of_data_set,
                                        argprsr.args.key_of_data]
                           if x is not None and x ] )

        if argprsr.args.io_with_config_file:

            base_obj.update( { k : v for k,v in argprsr.args.to_dict().items() 
                               if not k in argprsr.write_config_exclude_default })
            encds.set_cipher_unit(encipher_data_dict_key=argprsr.args.encipher_data_dict_key)
            base_obj = encds.cipher_unit.decipher(enc_object=base_obj, verbose=argprsr.args.verbose)
            
        encds.set_datatree(identifier=category,
                           base_obj=base_obj,
                           encipher_data_dict_key=argprsr.args.encipher_data_dict_key)

        if (argprsr.args.append_data and 
            (not argprsr.args.io_with_config_file) and
            isinstance(data_input_path, str) and data_input_path):
            encds.read_datatree(update=True, identifier=None, getall=True, index=None,
                                decipher=True, 
                                decipher_key=data_key[:encipher_depth],
                                decipher_entire_data=False, verbose=argprsr.args.verbose)
        raw_data = argprsr.args.argv[0] if len(argprsr.args.argv) == 1  else argprsr.args.argv
        encds.datatree[ data_key ] = raw_data
        encds.datatree[('system_info', 'date')] = datetime.datetime.now().ctime()

        if argprsr.args.verbose:
            sys.stdout.write("----- Input ---------------------------------------------------\n")
            print(encds.datatree)

        if argprsr.args.verbose:
            sys.stdout.write("----- Enciphered ----------------------------------------------\n")

        encds.encipher(*(data_key[:encipher_depth]), entire_data=False, verbose=argprsr.args.verbose)
        print(encds.datatree)

        if argprsr.args.io_with_config_file:
            for k,v in encds.datatree.to_dict().items():
                if k in argprsr.write_config_exclude_default:
                    continue
                argprsr.args[k] = v

        elif isinstance(data_output_path, str) and data_output_path:
            encds.save_datatree(encipher=False,
                                parent_obj=None, identifier=None, exclude_keys=[],
                                bulk=True, index=None,
                                f_perm=0o644, make_directory=True, d_perm=0o755, 
                                verbose=argprsr.args.verbose)
            
        if argprsr.args.save_config:
            argprsr.save_config_action()

        # if argprsr.args.verbose: # For debug
        #     sys.stdout.write("----- Re-Deciphered -------------------------------------------\n")
        #     encds.decipher(*(data_key[:encipher_depth]), entire_data=False, verbose=argprsr.args.verbose)
        #     print(encds.datatree)
        #     sys.stdout.write("---------------------------------------------------------------\n")

        return 

    #
    #
    #

    encds.set_cipher_unit(encipher_data_dict_key=argprsr.args.encipher_data_dict_key)
    for idx, argv_i in enumerate(argprsr.args.argv):
        enc_data_i   = encds.cipher_unit.encipher(raw_data=argv_i, verbose=argprsr.args.verbose)
        enc_bytes    = enc_data_i['data']
        dec_data_i   = encds.cipher_unit.decipher(enc_object=enc_data_i, verbose=argprsr.args.verbose)
        sys.stdout.write("---------------------------------------------------------------\n")
        sys.stdout.write("(%d) Input              : %s\n" % (idx, argv_i) )
        sys.stdout.write("---------------------------------------------------------------\n")
        sys.stdout.write("(%d) Enciphered         : %s\n" % (idx, enc_bytes) )
        sys.stdout.write("(%d) Enciphered data    : %s\n" % (idx, str(enc_data_i)) )
        sys.stdout.write("(%d) Deciphered (Check) : %s\n" % (idx, dec_data_i) )
        sys.stdout.write("---------------------------------------------------------------\n")

    if argprsr.args.save_config:
        argprsr.save_config_action()

    return



if __name__ == '__main__':
    main()

