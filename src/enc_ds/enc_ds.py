#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import string
import secrets
import inspect
import struct

import getpass
import io
import base64

import cryptography
import cryptography.hazmat.primitives.kdf.pbkdf2
import paramiko

import sshkeyring

from .datatree import DataTreeBase, DataTree

class EncDSUtil(object):
    """
    Base Utility Class
    """
    def __init__(self):
        pass

    @classmethod
    def GenMasterkey(cls, key_bits:int=512):
        kystr = ''.join([secrets.choice(string.ascii_letters + string.digits
                                        + string.punctuation) for i in range(key_bits)])
        return kystr
    
    @classmethod
    def GenSalt(cls, key_bits:int=512):
        return secrets.token_bytes((key_bits+7)//8)
    
    @classmethod
    def GenIV(cls, key_bits:int=96):
        # return secrets.randbits(key_bits)
        return secrets.token_bytes((key_bits+7)//8)
    
    @classmethod
    def CheckBytesLength(cls, data, key_bits:int=512, verbose:bool=False) -> bytes:
        u_data = data.encode(coding='utf-8') if isinstance(data,str) else data
        if u_data is None:
            if verbose:
                sys.stderr.write("[%s.%s:%d] New %d-bytes data is created recreated\n"
                                 % (cls.__name__, inspect.currentframe().f_code.co_name,
                                    inspect.currentframe().f_lineno, key_bits))
            return cls.GenSalt(key_bits=key_bits)
        if not isinstance(u_data, bytes):
            raise TypeError("[%s.%s:%d] Data Type is not bytes nor str (%s, %s)\n"
                            % (cls.__name__, inspect.currentframe().f_code.co_name, inspect.currentframe().f_lineno, type(u_data), str(u_data)))
        elif len(u_data)<(key_bits//8):
            raise ValueError("[%s.%s:%d] Warning: salt is too short. (len=%d<%d)\n"
                             % (cls.__name__, inspect.currentframe().f_code.co_name,
                                inspect.currentframe().f_lineno, len(u_data)<(key_bits//8)))
        return u_data

    @classmethod
    def ChooseHasher(cls, key_bits:int=512):
        hasher = cryptography.hazmat.primitives.hashes.Hash( cryptography.hazmat.primitives.hashes.SHA512() if key_bits>384 else 
                                                             ( cryptography.hazmat.primitives.hashes.SHA384() if key_bits>256 else 
                                                               ( cryptography.hazmat.primitives.hashes.SHA512_256() if key_bits>224 else 
                                                                 ( cryptography.hazmat.primitives.hashes.SHA512_224() ))))
        return hasher
        

    @classmethod
    def RehashBytesIfNeeded(cls, data:bytes|str=None, key_bits:int=512, 
                            hasher : cryptography.hazmat.primitives.hashes.HashAlgorithm=None,
                            verbose:bool=False) -> bytes:
        u_data = data.encode(coding='utf-8') if isinstance(data, str) else data
        if not isinstance(u_data, bytes):
            raise TypeError("[%s.%s:%d] Data type is not str/bytes/NoneType (but, %s)" 
                            % (cls.__name__, inspect.currentframe().f_code.co_name,
                               inspect.currentframe().f_lineno, type(data)))
        elif len(u_data)==key_bits//8:
            return u_data
        
        if verbose and False:
            sys.stderr.write("[%s.%s:%d] Info: Additonal hash for ssh-signature (original length %d != %d)\n"
                             % (cls.__name__, inspect.currentframe().f_code.co_name,
                                inspect.currentframe().f_lineno, len(u_data), key_bits//8))

        hasher = hasher if isinstance(hasher,cryptography.hazmat.primitives.hashes.HashAlgorithm) else cls.ChooseHasher(key_bits=key_bits)
        hasher.update(data)
        return hasher.finalize()

    @classmethod
    def SignBySSHkey(cls, ssh_private_key, data, algorithm:str="rsa-sha2-512", **kwds) -> bytes:
        if isinstance(ssh_private_key, paramiko.agent.PKey):
            return ssh_private_key.sign_ssh_data(paramiko.util.asbytes(data), algorithm)
        else:
            sys.stderr.write("[%s.%s:%d] Error : Neither agent_key nor local_key are available. (%s)\n"
                             % (self.__class__.__name__, inspect.currentframe().f_code.co_name, inspect.currentframe().f_lineno, str(self)))
            raise TypeError("Unknown ssh key object type")


    class SSHSignKDF(object):
        """
        Key Derivation Function utility w/ sigining by SSH key
    
        """
        def __init__(self, sshkey : paramiko.pkey.PKey,
                     salt:bytes|str = None, 
                     key_bits:int=512, iterations=1000000,
                     sshkeysign_algorithm:str="rsa-sha2-512",
                     hasher:cryptography.hazmat.primitives.hashes.HashAlgorithm=None, **kwds):
            super().__init__()
            
            self.__scope__  = self.__class__.__qualname__.removesuffix('.'+self.__class__.__name__)
            self.sshkey     = sshkey
            self.key_bits   = key_bits
            self.sshkeysign_algorithm = sshkeysign_algorithm
            self.iterations = iterations
            self.hasher     = (hasher if isinstance(hasher,cryptography.hazmat.primitives.hashes.HashAlgorithm)
                               else eval(self.__scope__).ChooseHasher(key_bits=key_bits))
            self.verbose    = kwds.get('verbose', False)
            self.salt       = eval(self.__scope__).CheckBytesLength(salt, key_bits=self.key_bits, verbose=self.verbose)

            self.kdf        = cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC(algorithm=cryptography.hazmat.primitives.hashes.SHA512(),
                                                                                   length=self.key_bits//8, salt=self.salt, iterations=self.iterations)
            
        def sign_by_sshkey(self, data:bytes|str, verbose:bool=False):
            sign = eval(self.__scope__).SignBySSHkey(self.sshkey, data,
                                                     algorithm=self.sshkeysign_algorithm, verbose=self.verbose)
            return eval(self.__scope__).RehashBytesIfNeeded(sign, key_bits=self.key_bits,
                                                            hasher=self.hasher, verbose=self.verbose)
                
        def derive(self, key_material:bytes|str, verbose:bool=False) -> bytes:
            u_sign = self.sign_by_sshkey(data=key_material, verbose=verbose)
            return self.kdf.derive(u_sign)
    
        def verify(self, key_material:bytes|str, expected_key=bytes|str, verbose:bool=False):
            u_sign = self.sign_by_sshkey(data=key_material, verbose=verbose)
            return self.kdf.verify(u_sign, expected_key)


class EncStoreUnit(EncDSUtil):
    """
    Base class : 

    """
    AES_GCM_KEYBITS  = 256
    AES_GCM_IVBITS   = 96 # 12*8
    KEY_HASHER       = cryptography.hazmat.primitives.hashes.Hash(cryptography.hazmat.primitives.hashes.SHA256())
    CONVERT_HEADER   = b'::CONVERTED::::'
    CONVERT_TALIER   = b'::::'
    CONVERT_BYTEODR  = 'big' # Network byte order : altavative: sys.byteorder
    STR_ENCODING     = 'utf-8'
    TAG_LENGTH_BYTES = 4

    CONVERT_TYPE_POSTFIXES = { bytearray: b'ARY',
                               int:       b'INT',
                               bool:      b'BOL',
                               float:     b'FLT',
                               complex:   b'CPX',
                               str:       b'STR',
                               None:      b'NON',
                               'raw':     b'RAW',
                               'unknown': b'UKW'}
    
    def __init__(self, **kwds):
        super().__init__(**kwds)

    @classmethod
    def __update_convert_header__(cls):
        cls.CONVERT_HEADER = __class__.__name__.encode(encoding=cls.STR_ENCODING)+b'::CONVERTED::'

    @classmethod
    def ToBytes(cls, val, verbose:bool=False) -> bytes :
        if val is None:
            return cls.CONVERT_HEADER+cls.CONVERT_TYPE_POSTFIXES.get(None)+bytes(0)

        if isinstance(val, bytes):
            return val

        prefix  = cls.CONVERT_HEADER
        prefix += cls.CONVERT_TYPE_POSTFIXES.get(type(val), 
                                                 cls.CONVERT_TYPE_POSTFIXES.get('unknown'))
        prefix += cls.CONVERT_TALIER
        
        if isinstance(val, bytearray):
            return prefix+bytes(val)
        
        if isinstance(val, int):
            return prefix+val.to_bytes(length=32, byteorder=cls.CONVERT_BYTEODR, signed=True)

        if isinstance(val, bool):
            return prefix+val.to_bytes()

        if isinstance(val, float):
            return prefix+struct.pack('!d', val)

        if isinstance(val, complex):
            return prefix+struct.pack('!dd', val.real, val.imag)

        if isinstance(val, str):
            return prefix+val.encode(encoding=cls.STR_ENCODING)

        try:
            if verbose:
                sys.stderr.write("[%s.%s:%d] Unsupported class: try to convert to str : %s\n"
                                 % (cls.__name__, inspect.currentframe().f_code.co_name,
                                    inspect.currentframe().f_lineno, type(val)))
            return prefix+type(val).encode(encoding=cls.STR_ENCODING)+cls.CONVERT_TALIER+str(val).encode(encoding=cls.STR_ENCODING)
        except:
            raise ValueError('Unsupported Type:'+type(val))
        
    @classmethod
    def FromBytes(cls, val:bytes, verbose:bool=False):
        if not val.startswith(cls.CONVERT_HEADER):
            return val

        if val.startswith(cls.CONVERT_TYPE_POSTFIXES.get(None)+cls.CONVERT_TALIER):
            return None

        sval = val.removeprefix(cls.CONVERT_HEADER)

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get('raw')+cls.CONVERT_TALIER):
            return sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get('raw')+cls.CONVERT_TALIER)

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get(bytearray)+cls.CONVERT_TALIER):
            return bytes(sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get(bytearray)+cls.CONVERT_TALIER))
        
        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get(int)+cls.CONVERT_TALIER):
            return int.from_bytes(sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get(int)+cls.CONVERT_TALIER),
                                  byteorder=cls.CONVERT_BYTEODR, signed=True)

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get(bool)+cls.CONVERT_TALIER):
            return bool.from_bytes(sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get(bool)+cls.CONVERT_TALIER))

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get(float)+cls.CONVERT_TALIER):
            return float(struct.unpack('!d', sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get(float)+cls.CONVERT_TALIER))[0])

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get(complex)+cls.CONVERT_TALIER):
            return complex(*struct.unpack('!dd', sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get(complex)+cls.CONVERT_TALIER)))
        

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get(str)+cls.CONVERT_TALIER):
            return sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get(str)+cls.CONVERT_TALIER).decode(encoding=cls.STR_ENCODING)

        if sval.startswith(cls.CONVERT_TYPE_POSTFIXES.get('unknown')+cls.CONVERT_TALIER):
            ssval   = sval.removeprefix(cls.CONVERT_TYPE_POSTFIXES.get('unknown')+cls.CONVERT_TALIER)
            hdridx  = ssval.find(cls.CONVERT_TALIER)
            clsname = ssval[:hdridx]
            sxval   = ssval[hdridx+len(cls.CONVERT_TALIER):]
            if verbose:
                sys.stderr.write("[%s.%s:%d] Unsupported class: Restored the converted strings (%s)\n"
                                 % (cls.__name__, inspect.currentframe().f_code.co_name,
                                    inspect.currentframe().f_lineno, clsname))
            return sxval.decode(encoding=cls.STR_ENCODING)

        return sval[sval.find(cls.CONVERT_TALIER)+len(cls.CONVERT_TALIER):]
        
    @classmethod
    def Enciphering(cls, raw_data,
                    cipher : cryptography.hazmat.primitives.ciphers.Cipher,
                    encipher_data_dict_key=False, verbose:bool=False)  -> bytes:

        if isinstance(raw_data, list):
            return [ cls.Enciphering(i, cipher=cipher, encipher_data_dict_key=encipher_data_dict_key)
                     for i in raw_data ]

        if isinstance(raw_data, (tuple, set, frozenset)):
            return type(raw_data)([ cls.Enciphering(i, cipher=cipher, encipher_data_dict_key=encipher_data_dict_key)
                                    for i in raw_data ])

        if isinstance(raw_data, dict):
            if encipher_data_dict_key:
                return { cls.Enciphering(k, cipher=cipher, encipher_data_dict_key=encipher_data_dict_key) :
                         cls.Enciphering(v, cipher=cipher, encipher_data_dict_key=encipher_data_dict_key)
                         for k,v in raw_data.items() }
            else:
                return { k : cls.Enciphering(v, cipher=cipher, encipher_data_dict_key=encipher_data_dict_key)
                         for k,v in raw_data.items() }
            
        encryptr = cipher.encryptor()
        encryptd = encryptr.update(cls.ToBytes(raw_data, verbose=verbose)) + encryptr.finalize()
        l_tag    = len(encryptr.tag).to_bytes(length=cls.TAG_LENGTH_BYTES, byteorder=cls.CONVERT_BYTEODR, signed=False)
        return l_tag+encryptr.tag+encryptd
        
    @classmethod
    def Encipher(cls, raw_data,
                 master_key:str|bytes, sshkey : paramiko.pkey.PKey,
                 iterations=1000000,
                 kdf=None, key=None, iv=None, encipher_data_dict_key=False,
                 verbose=False) -> bytes:
        
        enc_kdf = kdf if isinstance(kdf, super().SSHSignKDF) else cls.SSHSignKDF(sshkey=sshkey, salt=None, 
                                                                                 key_bits=cls.AES_GCM_KEYBITS, iterations=iterations,
                                                                                 sshkeysign_algorithm="rsa-sha2-512",
                                                                                 hasher=cls.KEY_HASHER, verbose=verbose)
        enc_key = key if isinstance(key, bytes) else enc_kdf.derive(key_material=master_key, verbose=verbose)
        enc_iv  = iv  if isinstance(iv, bytes)  else cls.GenIV(key_bits=cls.AES_GCM_IVBITS)

        cphr = cryptography.hazmat.primitives.ciphers.Cipher(cryptography.hazmat.primitives.ciphers.algorithms.AES(enc_key),
                                                             cryptography.hazmat.primitives.ciphers.modes.GCM(enc_iv),
                                                             backend=cryptography.hazmat.backends.default_backend())
        
        encryptd = cls.Enciphering(raw_data, cipher=cphr, encipher_data_dict_key=encipher_data_dict_key, verbose=verbose)
        return (encryptd, enc_iv, enc_kdf.salt)

    
    @classmethod
    def Deciphering(cls, enc_data, enc_key:bytes, enc_iv:bytes,
                    decipher_data_dict_key=False, verbose:bool=False):

        if isinstance(enc_data, list):
            return [ cls.Deciphering(i, enc_key=enc_key, enc_iv=enc_iv, decipher_data_dict_key=decipher_data_dict_key)
                     for i in enc_data ]

        if isinstance(enc_data, (tuple, set, frozenset)):
            return type(enc_data)([ cls.Deciphering(i, enc_key=enc_key, enc_iv=enc_iv, decipher_data_dict_key=decipher_data_dict_key)
                                    for i in enc_data ])

        if isinstance(enc_data, dict):
            if decipher_data_dict_key:
                return { cls.Deciphering(k, enc_key=enc_key, enc_iv=enc_iv, decipher_data_dict_key=decipher_data_dict_key) :
                         cls.Deciphering(v, enc_key=enc_key, enc_iv=enc_iv, decipher_data_dict_key=decipher_data_dict_key)
                         for k,v in enc_data.items() }
            else:
                return { k : cls.Deciphering(v, enc_key=enc_key, enc_iv=enc_iv, decipher_data_dict_key=decipher_data_dict_key)
                         for k,v in enc_data.items() }
        
        u_enc_data = enc_data.encode(encoding=cls.STR_ENCODING) if isinstance(enc_data,str) else enc_data

        if not isinstance(u_enc_data, bytes):
            raise TypeError("[%s.%s:%d] Data Type is not bytes nor str (%s) \n"
                            % (cls.__name__, inspect.currentframe().f_code.co_name,
                               inspect.currentframe().f_lineno, type(enc_data)))

        l_tag   = int.from_bytes(u_enc_data[:cls.TAG_LENGTH_BYTES], byteorder=cls.CONVERT_BYTEODR, signed=False)
        enc_tag = u_enc_data[cls.TAG_LENGTH_BYTES:cls.TAG_LENGTH_BYTES+l_tag]
        enc_val = u_enc_data[cls.TAG_LENGTH_BYTES+l_tag:]

        cphr = cryptography.hazmat.primitives.ciphers.Cipher(cryptography.hazmat.primitives.ciphers.algorithms.AES(enc_key),
                                                             cryptography.hazmat.primitives.ciphers.modes.GCM(enc_iv, enc_tag),
                                                             backend=cryptography.hazmat.backends.default_backend())
        decryptr = cphr.decryptor()
        decryptd = decryptr.update(enc_val) + decryptr.finalize()
        return cls.FromBytes(decryptd, verbose=verbose)

    @classmethod
    def Decipher(cls, enc_data, enc_iv:str|bytes,
                 salt:str|bytes, master_key:str|bytes, sshkey:paramiko.pkey.PKey,
                 kdf=None, key=None, iterations=1000000, decipher_data_dict_key=False, verbose=False) -> bytes:

        enc_kdf = kdf if isinstance(kdf, super().SSHSignKDF) else cls.SSHSignKDF(sshkey=sshkey, salt=salt, 
                                                                                 key_bits=cls.AES_GCM_KEYBITS, iterations=iterations,
                                                                                 sshkeysign_algorithm="rsa-sha2-512",
                                                                                 hasher=cls.KEY_HASHER, verbose=verbose)
        enc_key = key if isinstance(key, bytes) else enc_kdf.derive(key_material=master_key, verbose=verbose)

        u_enc_iv = enc_iv.encode(coding=cls.STR_ENCODING) if isinstance(enc_iv,str) else enc_iv
        if not isinstance(u_enc_iv, bytes):
            raise TypeError("[%s.%s:%d] IV Type is not bytes nor str (%s) \n"
                            % (cls.__name__, inspect.currentframe().f_code.co_name,
                               inspect.currentframe().f_lineno, type(enc_data)))
    
        decryptd = cls.Deciphering(enc_data, enc_key=enc_key, enc_iv=u_enc_iv,
                                   decipher_data_dict_key=decipher_data_dict_key, verbose=verbose)
        return decryptd

EncStoreUnit.__update_convert_header__()

class EncipherStorageUnit(EncStoreUnit):

    ENC_KEY_DATA    = 'data'
    ENC_KEY_IV      = 'iv'
    ENC_KEY_SALT    = 'salt'
    ENC_KEY_KDFMKEY = 'mkey'
    ENC_KEY_KDFPKEY = 'pkey'
    ENC_DICT_KEYS   = { ENC_KEY_DATA, ENC_KEY_IV, ENC_KEY_SALT, ENC_KEY_KDFMKEY, ENC_KEY_KDFPKEY }

    def __init__(self, master_key:str,
                 sshkey : paramiko.pkey.PKey, 
                 kdf_iterations=1000000,
                 encipher_data_dict_key=False,
                 name='', identifier=None, default_idenfitier=True,  **kwds):
        super().__init__(**kwds)

        self.file_encoding          = 'utf-8'
        self.sshkey                 = sshkey
        self.kdf_iterations         = kdf_iterations
        self.encipher_data_dict_key = encipher_data_dict_key
        
        self.name                    = name
        if isinstance(identifier, str) and identifier:
            self.identifier =  identifier
        elif default_idenfitier:
            self.identifier = ' '.join([self.__class__.__name__, self.name]) if isinstance(self.name,str) and self.name else self.__class__.__name__
        else:
            self.identifier = None

        # self.master_key             = master_key if isinstance(master_key, str) and master_key else None
        self.set_masterkey(masterkey=master_key, length=16)

        
    def set_masterkey(self, masterkey:str = None, length:int=16, **kwd):
        self.master_key = masterkey if ( isinstance(masterkey, str) and 
                                         len(masterkey) >= length ) else self.__class__.GenMasterkey(key_bits=length)
        return self.master_key

    def get_hashed_masterkey(self) -> str:
        hasher = cryptography.hazmat.primitives.hashes.Hash(cryptography.hazmat.primitives.hashes.SHA256())
        hasher.update(self.master_key.encode(encoding=self.file_encoding))
        hashed_mkey = hasher.finalize()
        return base64.b64encode(hashed_mkey).decode(encoding=self.file_encoding)

    def get_sshkey_fingerprint(self) -> str:
        return base64.b64encode(self.sshkey.get_fingerprint()).decode(encoding=self.file_encoding)
    
    def encipher_by_sshkdf(self, raw_data, verbose=False):
        return self.__class__.Encipher(raw_data=raw_data,
                                       master_key=self.master_key, sshkey=self.sshkey,
                                       iterations=self.kdf_iterations,
                                       encipher_data_dict_key=self.encipher_data_dict_key, verbose=verbose)
    
    def decipher_by_sshkdf(self, enc_data, enc_iv:str|bytes, salt:str|bytes, verbose=False):
        return self.__class__.Decipher(enc_data=enc_data, enc_iv=enc_iv,
                                       salt=salt, master_key=self.master_key, sshkey=self.sshkey,
                                       iterations=self.kdf_iterations,
                                       decipher_data_dict_key=self.encipher_data_dict_key, verbose=verbose)

    def encipher(self, raw_data, verbose=False) -> dict:
        encryptd, enc_iv, salt = self.encipher_by_sshkdf(raw_data=raw_data, verbose=verbose)
        return {self.__class__.ENC_KEY_DATA: encryptd,
                self.__class__.ENC_KEY_IV:   enc_iv, 
                self.__class__.ENC_KEY_SALT: salt,
                self.__class__.ENC_KEY_KDFMKEY: self.get_hashed_masterkey(),
                self.__class__.ENC_KEY_KDFPKEY: self.get_sshkey_fingerprint()}

    def decipher(self, enc_object, verbose=False):
        if isinstance(enc_object, list):
            return [ self.decipher(i, verbose=verbose) for i in enc_object ]

        if isinstance(enc_object, (tuple, set, frozenset)):
            return type(enc_object)( [ self.decipher(i, verbose=verbose) for i in enc_object ])

        if isinstance(enc_object, dict):
            if self.__class__.ENC_DICT_KEYS.issubset(enc_object):
                if (enc_object.get(self.__class__.ENC_KEY_KDFMKEY) == self.get_hashed_masterkey()
                    and enc_object.get(self.__class__.ENC_KEY_KDFPKEY) == self.get_sshkey_fingerprint()):
                    return self.decipher_by_sshkdf(enc_data=enc_object.get(self.__class__.ENC_KEY_DATA), 
                                                   enc_iv=enc_object.get(self.__class__.ENC_KEY_IV),
                                                   salt=enc_object.get(self.__class__.ENC_KEY_SALT), verbose=verbose)
                else:
                    if verbose:
                        sys.stderr.write("[%s.%s:%d] Skip due to key the mismatch : master(read: %s, decipher %s), sshkey(read: %s, decipher %s)\n"
                                         % (cls.__name__, inspect.currentframe().f_code.co_name,
                                            inspect.currentframe().f_lineno,
                                            enc_object.get(self.__class__.ENC_KEY_KDFMKEY), self.get_hashed_masterkey(),
                                            enc_object.get(self.__class__.ENC_KEY_KDFPKEY), self.get_sshkey_fingerprint() ))
                    return enc_object
            else:
                return { k: self.decipher(v, verbose=verbose) for k, v in enc_object.items() }

        return enc_object

class CipherDataTree(DataTree, EncipherStorageUnit):

    def __init__(self, 
                 master_key:str,
                 sshkey:paramiko.pkey.PKey, 
                 base_obj={}, name='', 
                 identifier=None,
                 kdf_iterations=1000000,
                 encipher_data_dict_key=False,
                 default_idenfitier=True,  **kwds):

        self.name = name
        if isinstance(identifier, str) and identifier:
            self.common_id =  identifier
        elif default_idenfitier:
            self.common_id = ( ' '.join([self.__class__.__name__, self.name]) 
                               if isinstance(self.name,str) and self.name 
                               else self.__class__.__name__ )
        else:
            self.common_id = None

        DataTree.__init__(self, base_obj=base_obj, identifier=self.common_id)
        EncipherStorageUnit.__init__(self, master_key=master_key, sshkey=sshkey,
                                     kdf_iterations=kdf_iterations,
                                     encipher_data_dict_key=encipher_data_dict_key,
                                     name=name, identifier=self.common_id, 
                                     default_idenfitier=default_idenfitier,  **kwds)


    def encipher_node(self, *args, 
                      key:list|tuple=[], 
                      keys:list|tuple|set|frozenset=[], entire_data=False, verbose=False):
        if entire_data:
            enc_data = self.encipher(self.root_node, verbose=verbose)
            self.root_node = enc_data
            return enc_data

        buf = []
        if not tuple(args) in buf:
            buf.append(args)
        if not tuple(key) in buf:
            buf.append(key)
        for k in keys:
            if tuple(k) in buf:
                continue
            buf.append(key)

        enc_buf = []
        for k in buf:
            raw_data,flg = self.accessor_w_chk(data=self.root_node, idxs=k)
            if not flg:
                continue
            enc_data = self.encipher(raw_data, verbose=verbose)
            v, flg   = self.setter_w_chk(data=self.root_node, idxs=k, value=enc_data,
                                         padding=True, mixedtype=True, overwrite_innernode=True)
            enc_buf.append(v)

        return enc_buf

    def decipher_node(self, *args, 
                      key:list|tuple=[], 
                      keys:list|tuple|set|frozenset=[], entire_data=False, verbose=False):
        if entire_data:
            dec_data = self.decipher(enc_object=self.root_node, verbose=verbose)
            self.root_node = dec_data
            return dec_data

        buf = []
        if not tuple(args) in buf:
            buf.append(args)
        if not tuple(key) in buf:
            buf.append(key)
        for k in keys:
            if tuple(k) in buf:
                continue
            buf.append(key)

        dec_buf = []
        for k in buf:
            enc_data,flg = self.accessor_w_chk(data=self.root_node, idxs=k)
            if not flg:
                continue
            dec_data = self.decipher(enc_object=enc_data, verbose=verbose)
            v, flg   = self.setter_w_chk(data=self.root_node, idxs=k, value=dec_data,
                                         padding=True, mixedtype=True, overwrite_innernode=True)
            dec_buf.append(v)

        return dec_buf



class EncDataStorage(object):

    def __init__(self, storage_name:str, 
                 storage_masterkey:str=None,
                 data_identifier:str=None,
                 sshkey_passphrase:str=None, key_id:str=None,
                 key_bits:int=4096, min_passphrase_length:int=8, 
                 key_file_basename:str=None,
                 keypath_prefix:str=None,
                 keypath_private:str=None,
                 keypath_public:str=None,
                 use_openssh_keys:str=None,
                 allow_keyfile_overwrite:bool=False,
                 use_ssh_agent:bool = True,
                 invoke_ssh_agent:bool = True,
                 register_agent:bool = None, **args):

        self.storage_name = storage_name
        self.data_identifier = data_identifier if isinstance(data_identifier, str) and data_identifier else self.storage_name
        self.keyfile_bn   = key_file_basename if isinstance(key_file_basename, str) and key_file_basename else self.storage_name
        self.use_key_id   = key_id if isinstance(key_id, str) and key_id else sshkeyring.SSHKeyRing.Default_Key_Id()

        self.use_key_type = 'rsa'
        self.sshkey_sign_algorithm = "rsa-sha2-512"
        self.key_bits   = key_bits if isinstance(key_bits,int) else None

        self.keypathconf = {"prefix"  :             keypath_prefix   if isinstance(keypath_prefix,str)   and keypath_prefix   else None, 
                            "private" :             keypath_private  if isinstance(keypath_private,str)  and keypath_private  else None,
                            "public"  :             keypath_public   if isinstance(keypath_public,str)   and keypath_public   else None,
                            "seek_openssh_keydir" : use_openssh_keys if isinstance(use_openssh_keys,str) and use_openssh_keys else None}
        
        self.sshkey_passphrase = sshkey_passphrase

        self.allow_keyfile_overwrite = allow_keyfile_overwrite

        self.ssh_agent = {'use_agent':    use_ssh_agent,
                          'invoke_agent': invoke_ssh_agent,
                          'register_key': use_ssh_agent if register_agent is None else register_agent }

        self.rsa_public_exponent = args.get('rsa_public_exponent', 65537)
        self.min_passphrase_length = min_passphrase_length

        self.kdf_interactions = args.get('kdf_interactions', 1000000)

        # self.master_key_phrase = storage_masterkey
        self.set_masterkey(storage_masterkey)

        self.data_io = {'path':         None,
                        'in_path':      None,
                        'out_path':     None,
                        'format':       None,
                        'compress':     False,
                        'in_format':    None,
                        'out_format':   None,
                        'in_compress':  None,
                        'out_compress': None }

        self.base_data = args.get('base_data', {})

        self.sshkeyring     = None
        self.picked_keyinfo = None
        self.sshkey_use     = None
        self.cipher_unit    = None
        self.datatree       = None

    def set_masterkey(self, key_phrase:str=None):
        if isinstance(key_phrase,str) and key_phrase:
            self.master_key_phrase = key_phrase
            return

        self.master_key_phrase = getpass.getpass(prompt=('(%s)Enter Master Key Phrase: '
                                                         % (self.storage_name, )))
        if isinstance(self.master_key_phrase,str) and self.master_key_phrase:
            return

        raise ValueError("[%s.%s:%d] empty master key-phrase : %s\n"
                         % (__name__, inspect.currentframe().f_code.co_name,
                            inspect.currentframe().f_lineno, self.master_key_phrase))


    @classmethod
    def guess_format(cls, file_path:str):
        bn, fmt, comp = DataTree.path_format_extsplit(file_path)
        return (fmt,comp)

    @classmethod
    def set_path_ext(cls, file_path:str,
                     serialize_format:str=None, compress:str=None):
        srlz_fmt = ( serialize_format
                     if serialize_format in DataTree.SERIALIZE_FORMATS 
                     else DataTree.SERIALIZE_FORMATS[0] )
        return DataTree.path_format_addext(path=file_path,
                                           fmt=srlz_fmt, compress=compress)

    def path_adjust(self, f_path:str):
        return DataTree.path_format_addext(f_path, self.data_io['format'], self.data_io['compress'])
    
    def i_path_adjust(self, f_path:str):
        return DataTree.path_format_addext(f_path, 
                                           self.data_io['in_format']
                                           if isinstance(self.data_io['in_format'],str) and self.data_io['in_format']
                                           else self.data_io['format'],
                                           self.data_io['in_compress']
                                           if isinstance(self.data_io['in_compress'],str) and self.data_io['in_compress']
                                           else self.data_io['compress'])

    def o_path_adjust(self, f_path:str):
        return DataTree.path_format_addext(f_path, 
                                           self.data_io['out_format']
                                           if isinstance(self.data_io['out_format'],str) and self.data_io['out_format']
                                           else self.data_io['format'],
                                           self.data_io['out_compress']
                                           if isinstance(self.data_io['out_compress'],str) and self.data_io['out_compress']
                                           else self.data_io['compress'])

    @property
    def path(self):
        return self.data_io['path']
    
    @path.setter
    def path(self, f_path:str):
        self.data_io['path'] = self.path_adjust(f_path)

    @property
    def input_path(self):
        return self.data_io['in_path'] if isinstance(self.data_io['in_path'],str) and self.data_io['in_path'] else self.data_io['path']
    
    @input_path.setter
    def input_path(self, f_path:str):
        self.data_io['in_path'] = self.i_path_adjust(f_path)

    @property
    def output_path(self):
        return self.data_io['out_path'] if isinstance(self.data_io['out_path'],str) and self.data_io['out_path'] else self.data_io['path']

    @output_path.setter
    def output_path(self, f_path:str):
        self.data_io['out_path'] = self.o_path_adjust(f_path)


    @property
    def io_format(self):
        return self.data_io['format']

    @io_format.setter
    def io_format(self, value:bool):
        self.data_io['format'] = value

    @property
    def in_format(self):
        return self.data_io['in_format'] if isinstance(self.data_io['in_format'],str) and self.data_io['in_format'] else  self.data_io['format']

    @in_format.setter
    def in_format(self, value:bool):
        self.data_io['in_format'] = value

    @property
    def out_format(self):
        return self.data_io['out_format'] if isinstance(self.data_io['out_format'],str) and self.data_io['out_format'] else  self.data_io['format']

    @out_format.setter
    def out_format(self, value:bool):
        self.data_io['out_format'] = value


    def setup_sshkeyinfo(self, verbose:bool=False):
        # Prepare the SSH-Keyring
        self.sshkeyring = sshkeyring.SSHKeyRing(key_id_use=self.use_key_id, 
                                                key_type_use=self.use_key_type,
                                                rsa_key_bits_default=self.key_bits,
                                                keyfile_basename_default=self.keyfile_bn,
                                                private_keyfile_directory_default=self.keypathconf['private'],
                                                public_keyfile_directory_default=self.keypathconf['public'],
                                                keydir_prefix=self.keypathconf['prefix'],
                                                seek_openssh_keydir_default=self.keypathconf['seek_openssh_keydir'],
                                                passphrase=self.sshkey_passphrase)

        self.sshkeyring.refresh_keyinfo(use_local_key=True, use_ssg_agent=self.ssh_agent['use_agent'],
                                        seek_openssh_dir=self.keypathconf['seek_openssh_keydir'],
                                        decode_private_key=False, passphrase=None, passphrase_alist=None,
                                        keydir_prefix=None, privatekey_dir=None, publickey_dir=None, exclude_pattern=None,
                                        invoke_agent=self.ssh_agent['invoke_agent'],
                                        restore_environ=False, force_reconnect=False,
                                        verbose=verbose)


        if verbose:
            sys.stderr.write("[%s.%s:%d] Info :  Key ID in use : %s, Key Type in use : %s\n"
                            % (__name__, inspect.currentframe().f_code.co_name, inspect.currentframe().f_lineno,
                               self.sshkeyring.key_id_use, self.sshkeyring.key_type_use))
        
        # Pick-up ssh key
        self.picked_keyinfo = self.sshkeyring.pickup_keyinfo(key_id=self.use_key_id,
                                                             key_type=self.use_key_type)

        if self.picked_keyinfo is None: # Make key if not found
            new_keyinfo, ssh_add_status = self.sshkeyring.setup_new_sshkey(key_id=self.use_key_id, 
                                                                       key_type=self.use_key_type,
                                                                       key_bits=self.key_bits,
                                                                       passphrase=self.sshkey_passphrase,
                                                                       register_agent=self.ssh_agent['register_key'],
                                                                       keydir_prefix=self.keypathconf['prefix'],
                                                                       privatekey_dir=None, publickey_dir=None,
                                                                       keyfile_basename=self.keyfile_bn,
                                                                       privatekey_ext=None, publickey_ext=None,
                                                                       force_overwrite=self.allow_keyfile_overwrite,
                                                                       ecdsa_ec_type="secp256r1", rsa_public_exponent=self.rsa_public_exponent,
                                                                       min_passphrase_length=self.min_passphrase_length,
                                                                       verbose=verbose)
            self.picked_keyinfo = self.sshkeyring.pickup_keyinfo(key_id=self.use_key_id,
                                                             key_type=self.use_key_type)

            if self.picked_keyinfo is None:
                sys.stderr.write("[%s.%s:%d]:  No key pair is found ( key id: %s, type: %s)\n"
                                 % (__name__, inspect.currentframe().f_code.co_name,
                                    inspect.currentframe().f_lineno, self.sshkeyring.key_id_use, self.sshkeyring.key_type_use))
                sys.exit()

        if self.ssh_agent['use_agent']:
            if self.picked_keyinfo.agent_key is None:
                # Register key to SSH-agent
                self.picked_keyinfo.set_passphrase(passphrase=self.sshkey_passphrase, overwrite=False, 
                                                   min_passphrase_length=self.min_passphrase_length, verbose=verbose)
                self.picked_keyinfo.load_local_key(passphrase=self.sshkey_passphrase, verbose=verbose)
                self.sshkeyring.ssh_add_keyinfo(self.picked_keyinfo, verbose=verbose)
        else:
            if self.picked_keyinfo.local_key is None:
                self.picked_keyinfo.set_passphrase(passphrase=self.sshkey_passphrase, overwrite=False, 
                                                   min_passphrase_length=self.min_passphrase_length, verbose=verbose)
                self.picked_keyinfo.load_local_key(passphrase=self.sshkey_passphrase, verbose=verbose)

        self.sshkey_use = self.picked_keyinfo.agent_key if self.ssh_agent['use_agent'] else self.picked_keyinfo.local_key

        if verbose:
            sys.stderr.write("[%s.%s:%d] Info : Stored KeyInfo : %s\n"
                             % (__name__, inspect.currentframe().f_code.co_name,
                                inspect.currentframe().f_lineno, str(self.picked_keyinfo)))

    def gen_cipher_unit(self, identifier:str=None, storage_name:str=None,
                        master_key_phrase:str=None, encipher_data_dict_key:bool=False):

        master_key = master_key_phrase if isinstance(master_key_phrase, str) and master_key_phrase else self.master_key_phrase
        data_name  = storage_name if isinstance(storage_name, str) and storage_name else self.storage_name
        data_idntfr = ( identifier
                        if isinstance(identifier, str) and identifier
                        else ( self.data_identifier
                               if isinstance(self.data_identifier, str) and self.data_identifier 
                               else self.storage_name))

        enciphd_ds = EncipherStorageUnit(master_key=master_key_phrase, sshkey=self.sshkey_use, 
                                         kdf_iterations=self.kdf_interactions,
                                         name=data_name, identifier=data_idntfr,
                                         encipher_data_dict_key=encipher_data_dict_key)
        return enciphd_ds

    def set_cipher_unit(self, encipher_data_dict_key:bool=False):
        data_idntfr = ( self.data_identifier
                        if isinstance(self.data_identifier, str) and self.data_identifier 
                        else self.storage_name)
        self.cipher_unit = EncipherStorageUnit(master_key=self.master_key_phrase,
                                                sshkey=self.sshkey_use, 
                                                kdf_iterations=self.kdf_interactions,
                                                name=self.storage_name, identifier=data_idntfr,
                                                encipher_data_dict_key=encipher_data_dict_key)
        return self.cipher_unit
        
    def gen_datatree(self, storage_name:str=None,
                     identifier:str=None,  base_obj:dict|list|tuple=None,
                     master_key_phrase:str=None, encipher_data_dict_key:bool=False):
        master_key = master_key_phrase if isinstance(master_key_phrase, str) and master_key_phrase else self.master_key_phrase
        data_name  = storage_name if isinstance(storage_name, str) and storage_name else self.storage_name
        base_obj   = base_obj if isinstance(base_obj, (dict,list,tuple)) else self.base_data
        
        data_idntfr = ( identifier
                        if isinstance(identifier, str) and identifier
                        else ( self.data_identifier
                               if isinstance(self.data_identifier, str) and self.data_identifier 
                               else self.storage_name))

        cphd_dt    = CipherDataTree(master_key=master_key, sshkey=self.sshkey_use, 
                                    base_obj=base_obj, name=data_name,
                                    identifier=data_idntfr, encipher_data_dict_key=encipher_data_dict_key)
        return cphd_dt

    def set_datatree(self, identifier:str=None, 
                     base_obj:dict|list|tuple=None,
                     encipher_data_dict_key:bool=False):

        data_idntfr = ( identifier
                        if isinstance(identifier, str) and identifier
                        else ( self.data_identifier
                               if isinstance(self.data_identifier, str) and self.data_identifier 
                               else self.storage_name))
        self.datatree = CipherDataTree(master_key=self.master_key_phrase, sshkey=self.sshkey_use, 
                                       base_obj=base_obj if isinstance(base_obj, (dict, list, tuple)) else self.base_data,
                                       name=self.storage_name,
                                       identifier=data_idntfr, encipher_data_dict_key=encipher_data_dict_key)
        self.cipher_unit = self.datatree
        return self.datatree

    def read_datatree(self, datatree=None, file_path:str=None,
                      update=True, identifier=None, getall=True, index=None,
                      decipher:bool=False, decipher_key:list|tuple=[], 
                      decipher_keys:list|tuple|set|frozenset=[],
                      decipher_entire_data=True, verbose:bool=False):

        dtr = datatree if isinstance(datatree, CipherDataTree) else self.datatree

        data_idntfr = ( identifier
                        if isinstance(identifier, str) and identifier
                        else ( self.data_identifier
                               if isinstance(self.data_identifier, str) and self.data_identifier 
                               else self.storage_name))

        f_path = file_path if isinstance(file_path,str) and file_path else self.input_path

        dtr.read_serialized(file_path=f_path, update=update, 
                            identifier=data_idntfr, getall=getall, index=index,
                            verbose=verbose)

        if decipher:
            dtr.decipher_node(key=decipher_key, keys=decipher_keys,
                              entire_data=decipher_entire_data, verbose=verbose)


    def save_datatree(self, datatree=None, file_path:str=None,
                      encipher:bool=False, encipher_key:list|tuple=[], 
                      encipher_keys:list|tuple|set|frozenset=[], encipher_entire_data=False,
                      parent_obj=None, identifier=None, exclude_keys=[], bulk=True, index=None,
                      f_perm=0o644, make_directory:bool=True, d_perm=0o755, verbose:bool=False):

        dtr = datatree if isinstance(datatree, CipherDataTree) else self.datatree
        
        if encipher:
            dtr.encipher_node(key=encipher_key, keys=encipher_keys,
                              entire_data=encipher_entire_data, verbose=verbose)
        
        data_idntfr = ( identifier
                        if isinstance(identifier, str) and identifier
                        else ( self.data_identifier
                               if isinstance(self.data_identifier, str) and self.data_identifier 
                               else self.storage_name))

        f_path = file_path if isinstance(file_path,str) and file_path else self.output_path

        dtr.save_serialized(file_path=f_path, parent_obj=parent_obj, identifier=data_idntfr,
                            exclude_keys=exclude_keys, bulk=bulk, index=index,
                            f_perm=f_perm, make_directory=make_directory, d_perm=d_perm, verbose=verbose)


    def encipher(self, *args, 
                 key:list|tuple=[], 
                 keys:list|tuple|set|frozenset=[],
                 entire_data:bool=False, verbose:bool=False):
        return self.datatree.encipher_node(*args, key=key, keys=keys, 
                                           entire_data=entire_data, verbose=verbose)

    def decipher(self, *args, 
                 key:list|tuple=[], 
                 keys:list|tuple|set|frozenset=[],
                 entire_data:bool=False, verbose:bool=False):
        return self.datatree.decipher_node(*args, key=key, keys=keys,
                                           entire_data=entire_data, verbose=verbose)


if __name__ == "__main__":
    
    def main():
        import pydoc
        pydoc.help = pydoc.Helper(output=sys.stdout)
        help(EncDSUtil)
        help(EncDSUtil.SSHSignKDF)
        help(EncStoreUnit)
        help(EncipherStorageUnit)
        help(DataTreeBase)
        help(DataTree)
        help(CipherDataTree)
        help(EncDataStorage)
        return

    main()
