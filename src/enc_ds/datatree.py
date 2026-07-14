#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
import io
import collections.abc

import inspect
import copy
import base64 

import json
import yaml
import toml
import configparser
import bz2
import gzip
import lzma

from typing import Union

class DataTreeBase:

    @classmethod
    def accessor_w_chk(cls, data, idxs):
        if idxs is None:
            return data
        for idx in idxs:
            if isinstance(data, dict):
                if idx in data:
                    data = data[idx]
                else:
                    return (None, False)
            elif isinstance(data, (list, tuple)):
                try:
                    idx = int(idx)
                except:
                    return (None, False)
                if isinstance(idx, int) and 0 <= idx and idx < len(data):
                    data = data[idx]
                else:
                    return (None, False)
            else:
                return (None, False)
        return (data, True)

    @classmethod
    def pddlst(cls, buf=None, idx=0, paddingvalue=None):
        if buf is None:
            n_padding =  (-idx) if idx < 0 else (idx+1)
            return [ paddingvalue, ] * n_padding
        retv=copy.deepcopy(list(buf))
        if idx>=0 and idx>=len(buf):
            n_padding = idx+1-len(buf)
            retv.extend([paddingvalue, ]*n_padding)
        if idx<0 and len(buf)+idx<0:
            n_padding = -(len(buf)+idx)
            retv[:0] = [paddingvalue, ]*n_padding
        return retv
    
    @classmethod
    def setter_w_chk(cls, data, idxs, value, padding=True,
                     mixedtype=False, overwrite_innernode=True, paddingvalue=None): 
        if isinstance(idxs, (list,tuple)):
            if len(idxs)>0:
                idx    = idxs[0]
                subidx = idxs[1:]
            else:
                return (copy.deepcopy(value), True)
        elif isinstance(idxs, int) or isinstance(idxs, collections.abc.Hashable):
            idx    = idxs
            subidx = []
        else:
            return (copy.deepcopy(value), True)
    
        flg_ok = False
        if isinstance(data, (list, tuple)):
            try:
                i_idx = int(idx)
            except:
                i_idx = idx
                
            if isinstance(i_idx, int):
                if not padding and ( i_idx>=len(data) or len(data)+i_idx<0 ):
                    return (data, False)
                ret_val = cls.pddlst(buf=data, idx=i_idx, paddingvalue=paddingvalue)
                ret_val[i_idx], flg_ok = cls.setter_w_chk(ret_val[i_idx], subidx, value,
                                                        padding=padding, mixedtype=mixedtype,
                                                        overwrite_innernode=overwrite_innernode,
                                                        paddingvalue=paddingvalue)
                return (tuple(ret_val) if isinstance(data, tuple) else ret_val, flg_ok)
            else:
                ret_val = { i: v for i,v in enumerate(data) }
                child   = ret_val[i_idx] if i_idx in ret_val else paddingvalue
                ret_val[i_idx], flg_ok = cls.setter_w_chk(child, subidx, value,
                                                          padding=padding, mixedtype=mixedtype,
                                                          overwrite_innernode=overwrite_innernode,
                                                          paddingvalue=paddingvalue)
                return (ret_val, flg_ok)
        elif isinstance(data, dict):
            ret_val = copy.deepcopy(data)
            child = ret_val[idx] if idx in ret_val else paddingvalue
            ret_val[idx], flg_ok = cls.setter_w_chk(child, subidx, value,
                                                    padding=padding, mixedtype=mixedtype,
                                                    overwrite_innernode=overwrite_innernode,
                                                    paddingvalue=paddingvalue)
            return (ret_val, flg_ok)
        elif not overwrite_innernode:
            return (data, False)
        else:
            try:
                i_idx = int(idx)
            except:
                i_idx = idx
                
            if mixedtype and isinstance(i_idx, int):
                if not padding:
                    if  i_idx>0 or i_idx<-1:
                        return (data, False)
                    else:
                        i_idx=0
                
                ret_val = cls.pddlst(buf=None, idx=i_idx, paddingvalue=paddingvalue)
                ret_val[i_idx], flg_ok = cls.setter_w_chk(ret_val[i_idx], subidx, value,
                                                          padding=padding, mixedtype=mixedtype,
                                                          overwrite_innernode=overwrite_innernode,
                                                          paddingvalue=paddingvalue)
            else:
                ret_val = {idx: paddingvalue}
                ret_val[idx], flg_ok = cls.setter_w_chk(ret_val[idx], subidx, value,
                                                        padding=padding, mixedtype=mixedtype,
                                                        overwrite_innernode=overwrite_innernode,
                                                        paddingvalue=paddingvalue)
        
        return (ret_val, flg_ok)

    @classmethod
    def recursive_update(cls, new_value=None, base_value=None, type_override=False):
        """
        Merge dict-type variable base_value recurcively by new_value:
        """
        if new_value is None:
            new_value={}

        if base_value is None:
            base_value={}

        if not isinstance(new_value, (dict, list, tuple)):
            return new_value
    
        if not isinstance(base_value, (dict, list, tuple)):
            return new_value
    
        # Dict - Dict
        if isinstance(new_value, dict):
            if isinstance(base_value, dict):
                merged = {}
                xkeys = set(new_value.keys())
                ykeys = set(base_value.keys())
                for k in xkeys.difference(ykeys):
                    merged[k] = new_value[k]
                for k in ykeys.difference(xkeys):
                    merged[k] = base_value[k]
                for k in xkeys.intersection(ykeys):
                    merged[k] = cls.recursive_update(new_value[k], base_value[k], 
                                                     type_override=type_override)
                return merged
        # List - List
        if isinstance(new_value, (list, tuple)):
            if isinstance(base_value, (list, tuple)):
                n_merged = max(len(new_value),len(base_value))
                merged =  n_merged * [None]
                for i in range(n_merged):
                    if i<len(new_value):
                        if i<len(base_value):
                            merged[i] = cls.recursive_update(new_value=new_value[i],
                                                             base_value=base_value[i],
                                                             type_override=type_override)
                        else:
                            merged[i] = new_value[i]
                    elif i<len(base_value):
                        merged[i] = base_value[i]
                    else:
                        break

                return merged if isinstance(base_value, list) else tuple(merged)
    
        if type_override:
            if isinstance(new_value, dict):
                # Dict - List
                x_keys = set(new_value.keys())
                base_keys = x_keys.difference(set([iy for iy in range(len(base_value))]
                                                  +[str(iy) for iy in range(len(base_value))]))
                merged = { xk: new_value[xk] for xk in base_keys }
    
                n_keys = set([ iy for iy in range(len(base_value)) 
                               if (not iy in x_keys) and (not str(iy) in x_keys) ])
                merged.update( { yk : base_value[yk] for yk in n_keys } )
    
                i_keys = set([ iy for iy in range(len(base_value)) if     iy  in x_keys])
                s_keys = set([ iy for iy in range(len(base_value)) if str(iy) in x_keys])
                for yk in i_keys:
                    merged[yk] = cls.recursive_update(new_value=new_value[yk],
                                                      base_value=base_value[yk],
                                                      type_override=type_override)
                for yk in s_keys:
                    s_yk = str(yk)
                    merged[s_yk] = cls.recursive_update(new_value=new_value[s_yk], 
                                                        base_value=base_value[yk],
                                                        type_override=type_override)
                return merged
            else: 
                # List - Dict
                merged = len(new_value)*[None]
    
                ymkeys = []
                for ix,xv in enumerate(new_value):
                    yv = base_value.get(ix)
                    if yv is None:
                        yv = base_value.get(str(ix))
                        if yv is not None:
                            ymkeys.append(str(ix))
                    else:
                        ymkeys.append(ix)
                    merged[ix] = xv if yv is None else cls.recursive_update(new_value=xv,
                                                                            base_value=yv,
                                                                            type_override=type_override)
    
    
                for yk,yv in base_value.items():
                    if yk in ymkeys:
                        continue
                    try:
                        iy = int(yk)
                    except:
                        iy = -1
                        sys.stderr.write("[%s.%s:%d] Warning: Non-integer-like key! : %s.\n"
                                         % (__name__, inspect.currentframe().f_code.co_name,
                                            inspect.currentframe().f_lineno, yk))
                        continue
    
                    if iy<len(new_value):
                        continue
    
                    if iy>=len(merged):
                        merged += (iy+1-len(merged))*[None]
                                
                    merged[iy] = yv
    
                return type(new_value)(merged)
        # else: # type_override == False
        if isinstance(base_value, dict):
            # List - Dict
            y_keys = set(base_value.keys())
            base_keys = y_keys.difference(set([ix for ix in range(len(new_value))]
                                              +[str(ix) for ix in range(len(new_value))]))
            
            merged = { yk: base_value[yk] for yk in base_keys }
            
            n_keys = set([ ix for ix in range(len(new_value))
                           if (not ix in y_keys) and (not str(ix) in y_keys) ])
            merged.update( { xk : new_value[xk] for xk in n_keys } )
    
            i_keys = set([ ix for ix in range(len(new_value)) if     ix  in y_keys])
            s_keys = set([ ix for ix in range(len(new_value)) if str(ix) in y_keys])
            for xk in i_keys:
                merged[xk] = cls.recursive_update(new_value=new_value[xk],
                                                           base_value=base_value[xk],
                                                           type_override=type_override)
            for xk in s_keys:
                s_xk = str(xk)
                merged[s_xk] = cls.recursive_update(new_value=new_value[xk],
                                                             base_value=base_value[s_xk],
                                                             type_override=type_override)
            return merged
        else: 
            # Dict - List
            merged = len(base_value)*[None]
            
            xmkeys = []
            for iy,yv in enumerate(base_value):
                xv = new_value.get(iy)
                if xv is None:
                    xv = new_value.get(str(iy))
                    if xv is not None:
                        xmkeys.append(str(iy))
                else:
                    xmkeys.append(iy)
                merged[iy] = yv if xv is None else cls.recursive_update(new_value=xv, base_value=yv,
                                                                                 type_override=type_override)
    
    
            for xk,xv in new_value.items():
                if xk in xmkeys:
                    continue
                try:
                    ix = int(xk)
                except:
                    ix = -1
                    sys.stderr.write("[%s.%s:%d] Warning: Non-integer-like key! : %s.\n"
                                     % (__name__, inspect.currentframe().f_code.co_name,
                                        inspect.currentframe().f_lineno, xk))
                    continue
    
                if ix<len(base_value):
                    continue
    
                if ix>=len(merged):
                    merged += (ix+1-len(merged))*[None]
                                
                    merged[ix] = xv
    
            return type(base_value)(merged)
    
        return new_value

    @classmethod
    def update(cls, data, node_names=None,
               base_obj:dict=None, list_mixed=False, type_override=False):
        nm_list = node_names.keys() if isinstance(node_names, dict) else node_names
        buf_raw = buf_fmt = data
        for rnm in reversed(nm_list):
            buf_fmt = int(rnm)*[None]+[buf_fmt] if ( list_mixed and type_override 
                                                     and isinstance(rnm, int) ) else {rnm: buf_fmt}
        return cls.recursive_update(new_value=buf_fmt,
                                    base_value=base_obj, type_override=type_override)


    @classmethod
    def calc_length(cls, obj):
        l = 0 
        if isinstance(obj, dict):
            for v in obj.values():
                l += cls.calc_length(v)
        elif isinstance(obj,(list, tuple)):
            for v in obj:
                l += cls.calc_length(v)
        else:
            l = 1
        return l

    @classmethod
    def get_keys(cls, obj, upper=None, buf=None):
        buf   = buf   if isinstance(buf, list)   else []
        upper = upper if isinstance(upper, list) else []
        if isinstance(obj,dict):
            for k,v in obj.items():
                cls.get_keys(v, upper=upper+[k], buf=buf)
        elif isinstance(obj,(list,tuple)):
            for k,v in enumerate(obj):
                cls.get_keys(v, upper=upper+[k], buf=buf)
        else:
            buf.append(tuple(upper))
        return buf

    @classmethod
    def get_values(cls, obj, buf=None):
        buf   = buf if isinstance(buf, list) else []
        if isinstance(obj,dict):
            for k,v in obj.items():
                cls.get_values(v, buf=buf)
        elif isinstance(obj,(list,tuple)):
            for k,v in enumerate(obj):
                cls.get_values(v, buf=buf)
        else:
            buf.append(obj)
        return buf

    @classmethod
    def get_items(cls, obj, upper=None, buf=None):
        buf   = buf   if isinstance(buf, list)   else []
        upper = upper if isinstance(upper, list) else []

        if isinstance(obj,dict):
            for k,v in obj.items():
                cls.get_items(v, upper=upper+[k], buf=buf)
        elif isinstance(obj,(list,tuple)):
            for k,v in enumerate(obj):
                cls.get_items(v, upper=upper+[k], buf=buf)
        else:
            buf.append((tuple(upper), obj))
        return buf

    @classmethod
    def find_key(cls, obj, keyset=None, leaf_node=False, negate=True):
        if keyset is None:
            keyset = []

        if len(keyset)<=0:
            if negate:
                return True if leaf_node and isinstance(obj, (dict, list, tuple)) else False
            else:
                return False if leaf_node and isinstance(obj, (dict, list, tuple)) else True
        
        ckey = keyset[0]
        flg_match = True if negate else False
        ptr_child = None
        if isinstance(obj, dict):
            if ckey in obj.keys():
                flg_match = False if negate else True
                ptr_child = obj[ckey]
        elif isinstance(obj, (list,tuple)):
            try:
                cidx = int(ckey)
                if cidx>=0 and cidx<len(obj):
                    flg_match = False if negate else True
                    ptr_child = obj[cidx]
            except:
                pass
        else:
            flg_match = True if negate else False
    
        if isinstance(ptr_child, (dict,list,tuple)):
            if len(keyset)==1:
                if negate:
                    flg_match = True if leaf_node else flg_match
                else:
                    flg_match = False if leaf_node else flg_match
            elif (negate and (not flg_match)) or ((not negate) and flg_match): 
                flg_child = cls.find_key(obj=ptr_child, keyset=keyset[1:], leaf_node=leaf_node, negate=negate)
                flg_match = ( (not flg_match ) and flg_child ) if negate else ( flg_match and flg_child )
        return flg_match

    @classmethod
    def find_keys(cls, obj, keyset_list=None, leaf_node=False, negate=True):
        if keyset_list is None:
            keyset_list = []

        return [ cls.find_key(obj, keyset=keyset,leaf_node=leaf_node,
                              negate=negate) for keyset in keyset_list ]
    @classmethod
    def find_keys_alist(cls, obj, keyset_list=None, leaf_node=False, negate=True):
        if keyset_list is None:
            keyset_list = []

        return { tuple(keyset) : cls.find_key(obj, keyset=keyset, leaf_node=leaf_node, 
                                              negate=negate) for keyset in keyset_list }

    @classmethod
    def find_value(cls, obj, keyset=None, leaf_node=False):
        if keyset is None:
            keyset = []

        if len(keyset)<=0:
            return (False, None) if leaf_node and isinstance(obj, (dict, list, tuple)) else (True, obj)

        ckey = keyset[0]
        flg_match = False
        ptr_child = None
        if isinstance(obj, dict):
            if ckey in obj.keys():
                flg_match = True
                ptr_child = obj[ckey]
        elif isinstance(obj, (list,tuple)):
            try:
                cidx = int(ckey)
                if cidx>=0 and cidx<len(obj):
                    flg_match = True
                    ptr_child = obj[cidx]
            except:
                pass
            
        if isinstance(ptr_child, (dict,list,tuple)):
            if len(keyset)>1:
                flg_match, ptr_child = cls.find_value(obj=ptr_child, keyset=keyset[1:], leaf_node=leaf_node)
            elif leaf_node:
                flg_match = False
                ptr_child = None

        return (flg_match, ptr_child)

    @classmethod
    def find(cls, obj, *arg, leaf_node=False):
        flg_match, ptr_child = cls.find_value(obj=obj, keyset=arg, leaf_node=leaf_node)
        return ptr_child

    @classmethod
    def find_values(cls, obj, keyset_list=None, leaf_node=False):
        if keyset_list is None:
            keyset_list = []

        buf = []
        for keyset in keyset_list:
            flg,v = cls.find_value(obj, keyset=keyset, leaf_node=leaf_node)
            if flg:
                buf.append(v)
        return buf

    @classmethod
    def find_items(cls, obj, keyset_list=None, leaf_node=False):
        if keyset_list is None:
            keyset_list = []
        buf = {}
        for keyset in keyset_list:
            flg,v = cls.find_value(obj, keyset=keyset, leaf_node=leaf_node)
            if flg:
                buf.update( { tuple(keyset) : v } )
        return buf

    def set_value(cls, obj, keyset, value):
        if len(keyset)==1:
            obj[keyset] = value

        ckey = keyset[0]
        flg_match = False
        ptr_child = None
        if isinstance(obj, dict):
            if ckey in obj.keys():
                flg_match = True
                ptr_child = obj[ckey]
        elif isinstance(obj, (list,tuple)):
            try:
                cidx = int(ckey)
                if cidx>=0 and cidx<len(obj):
                    flg_match = True
                    ptr_child = obj[cidx]
            except:
                pass
            
        if isinstance(ptr_child, (dict,list,tuple)):
            if len(keyset)>1:
                flg_match, ptr_child = cls.find_value(obj=ptr_child, keyset=keyset[1:], leaf_node=leaf_node)
            elif leaf_node:
                flg_match = False
                ptr_child = None

        return (flg_match, ptr_child)

    @classmethod
    def skim_data_tree(cls, obj, keyindexes):

        EMPTY = object()
    
        def clone_node(node):
            if node is EMPTY:
                return EMPTY
            if isinstance(node, dict):
                return { k: clone_node(v) for k, v in node.items() }
            if isinstance(node, list):
                return [ clone_node(v) for v in node ]
            if isinstance(node, tuple):
                return tuple( clone_node(v) for v in node )
            return copy.deepcopy(node)
    
        def to_int_index(key):
            try:
                return key if isinstance(key, int) else int(key)
            except (TypeError, ValueError):
                return None
    
        def extract_node(curr_node, keys):
            if len(keys) <= 0:
                return (clone_node(curr_node), True)
            
            c_key = keys[0]
            subkeys = keys[1:]
    
            if isinstance(curr_node, dict):
                if c_key not in curr_node:
                    return (EMPTY, False)
    
                child_node, flg = extract_node(curr_node[c_key], subkeys)
                if not flg:
                    return (EMPTY, False)
    
                return ( {c_key: child_node }, True)
    
            if isinstance(curr_node, (list, tuple)):
                i_key = to_int_index(c_key)
    
                if i_key is None or i_key < 0 or i_key >= len(curr_node):
                    return (EMPTY, False)
    
                child_node, flg = extract_node(curr_node[i_key], subkeys)
                if not flg:
                    return (EMPTY, False)
    
                buf = [EMPTY] * len(curr_node)
                buf[i_key] = child_node
    
                return ( tuple(buf) if isinstance(curr_node, tuple) else buf, True)
    
            return (EMPTY, False)
    
        def merge_data(dest_node, added_node):
            if dest_node is EMPTY:
                return clone_node(added_node)
    
            if added_node is EMPTY:
                return dest_node
    
            if isinstance(dest_node, dict) and isinstance(added_node, dict):
                merged = clone_node(dest_node)
    
                for key, val in added_node.items():
                    merged[key] = merge_data(merged.get(key, EMPTY), val)
    
                return merged
    
            if isinstance(dest_node, (list, tuple)) and isinstance(added_node, (list, tuple)):
                n_merged = max(len(dest_node), len(added_node))
                merged = []
    
                for i in range(n_merged):
                    dest_val  = dest_node[i] if i < len(dest_node) else EMPTY
                    added_val = added_node[i] if i < len(added_node) else EMPTY
    
                    merged.append(merge_data(dest_val, added_val))
    
                if isinstance(dest_node, tuple) and isinstance(added_node, tuple):
                    return tuple(merged)
    
                return merged
    
            return clone_node(added_node)
    
        def finalize(node):
            if node is EMPTY:
                return None
    
            if isinstance(node, dict):
                return {k: finalize(v) for k, v in node.items()}
    
            if isinstance(node, list):
                return [ finalize(v) for v in node ]
    
            if isinstance(node, tuple):
                return tuple( finalize(v) for v in node )
    
            return node
    
        retv = EMPTY
        for keys in keyindexes:
            if not isinstance(keys, (list, tuple)):
                keys = (keys,)
            extracted, flg = extract_node(obj, list(keys))
            if flg:
                retv = merge_data(retv, extracted)
    
        if retv is EMPTY:
            return type(obj)()
        return finalize(retv)
    
    @classmethod
    def rest_data_tree(cls, obj, keyindexes:list):
    
        def mask_tree(curr_node, keys:list):
            if len(keys)<=0:
                return (None, True)
            if isinstance(curr_node, dict) and keys[0] in curr_node.keys():
                cnode, flg = mask_tree(curr_node[keys[0]], keys[1:])
                if flg is True:
                    del curr_node[keys[0]]
                else:
                    curr_node[keys[0]] = cnode
                if len(curr_node)<=0:
                    return (None, True)
                return (curr_node, False)
            elif isinstance(curr_node, (list, tuple)):
                try:
                    i_key = keys[0] if isinstance(keys[0], int) else int(keys[0])
                except:
                    return (curr_node, False)
                curr_node_x = list(curr_node)

                if i_key < 0 or i_key >= len(curr_node_x):
                    return (curr_node, False)
                
                cnode, flg = mask_tree(curr_node_x[i_key], keys[1:])
                if flg is True:
                    curr_node_x[i_key] = None
                else:
                    curr_node_x[i_key] = cnode
                return (type(curr_node)(curr_node_x), False)
            return (curr_node, False)
    
        buf = copy.deepcopy(obj)
        for keys in keyindexes:
            msked,flg_ok = mask_tree(buf, keys)
            buf = msked
            
        def cleanup(obj, ref):
            if isinstance(obj, dict):
                if isinstance(ref, dict):
                    cleaned = { k: cleanup(v, ref.get(k)) for k, v in obj.items() if not ( v is None and ref.get(k) is not None ) }
                    return cleaned if len(cleaned)>0 else None
                else:
                    return None
            elif isinstance(obj, (list, tuple)):
                if isinstance(ref, type(obj)):
                    cleaned = [ cleanup(v, ref[i]) for i, v in enumerate(obj) ]
                    flg = any( ( ival is not None or ref[idx] is None )  for idx,ival in enumerate(cleaned) )
                    return type(obj)(cleaned) if flg else None
                else:
                    return None
            else:
                return obj
    
        buf = cleanup(buf, obj)
        return buf

class DataTree(DataTreeBase):

    SERIALIZE_KEY_TYPE  = '__type__'
    SERIALIZE_KEY_VALUE = '__value__'
    SERIALIZE_DICT_KEYS = { SERIALIZE_KEY_TYPE, SERIALIZE_KEY_VALUE }

    COMPRESS_EXT      = ('.bz2', '.gz', '.xz')
    SERIALIZE_FORMATS = ('json', 'JSON', 'yaml', 'yml', 'YAML', 'YML', 'ini', 'INI', 'toml', 'TOML')

    SERIALIZE_KEY_TYPE  = '__type__'
    SERIALIZE_KEY_VALUE = '__value__'
    SERIALIZE_DICT_KEYS = { SERIALIZE_KEY_TYPE, SERIALIZE_KEY_VALUE }

    ROOT_NODE_LABEL_DEFAULT = 'DEFAULT_VALUE'

    def __init__(self, base_obj=None, identifier=None, ):
        self._base                   = super()
        self.root_node               = self.__class__.type_adjust_inndernode(base_obj)
        self.mixedtype               = True
        self.file_encoding           = 'utf-8'
        self.json_indent             = 4
        self.yaml_default_flow_style = False
        self.toml_encoder            = None
        self.identifier              = identifier if isinstance(identifier,str) and identifier else self.__class__.__name__

    @classmethod
    def type_adjust_inndernode(cls, obj):
        if isinstance(obj, DataTree):
            return obj.root_node
        elif isinstance(obj, (dict, list, tuple)):
            return obj
        elif isinstance(obj, (set, frozenset)):
            return list(obj)
        return [obj]


    def set_rootnode(self, obj):
        self.root_node = self.__class__.type_adjust_inndernode(obj)

    def merge(self, obj, type_override=True):
        self.root_node = self._base.recursive_update(new_value=self.__class__.type_adjust_inndernode(obj), 
                                                     base_value=self.root_node,
                                                     type_override=type_override)

    def lengh(self):
        return self._base.calc_length(obj=self.root_node)

    def __len__(self):
        return self._base.calc_length(obj=self.root_node)

    def keys(self):
        return self._base.get_keys(obj=self.root_node)
    
    def values(self):
        return self._base.get_values(obj=self.root_node)

    def items(self):
        return self._base.get_items(obj=self.root_node)

    def value(self, keyset, leaf_node=False):
        return self._base.find_value(obj=self.root_node, 
                                     keyset=keyset, leaf_node=leaf_node)

    def getter(self, *key):
        v, flg = self._base.accessor_w_chk(data=self.root_node, idxs=key)
        return v


    def setter(self, *key, value=None, padding=True,
               mixedtype=True, overwrite_innernode=True):
        v, flg = self._base.setter_w_chk(data=self.root_node,
                                         idxs=key, value=value,
                                         padding=padding, mixedtype=mixedtype,
                                         overwrite_innernode=overwrite_innernode)
        if flg:
            self.root_node = v

        return flg

    def __getitem__(self, key):
        v, flg = self._base.accessor_w_chk(data=self.root_node, idxs=key)
        return v

    def __setitem__(self, key, value):
        v,flg = self._base.setter_w_chk(data=self.root_node,
                                        idxs=key, value=value, padding=True, 
                                        mixedtype=self.mixedtype, overwrite_innernode=True)
        if not flg:
            raise KeyError(key)
        self.root_node = v

    def __str__(self):
        desc = "# class <%s> : identifier=%s\n" % (self.__class__.__name__, self.identifier )
        for k,v in self.items():
            desc += "# %s --> %s\n" % (str(k), str(v))
        return desc

    def __repr__(self):
        desc = "# class <%s> : identifier=%s\n" % (self.__class__.__name__, self.identifier )
        for k,v in self.items():
            desc += "# %s --> %s\n" % (k.__repr__(), v.__repr__())
        return desc

    def is_validkey(self, keyset=None, 
                    leaf_node=False, negate=True):
        if keyset_list is None:
            keyset_list = []
        return self._base.find_key(obj=self.root_node, keyset=keyset, 
                                   leaf_node=leaf_node, negate=negate)

    def to_dict(self):
        if isinstance(self.root_node, DataTree):
            self.root_node = self.__dict__(self.root_node.root_node)
        elif isinstance(self.root_node, (list, tuple, set, frozenset)):
            return { i: v for i,v in enumerate(self.root_node) }
        elif isinstance(self.root_node, dict):
            return self.root_node
        return { self.__class__.ROOT_NODE_LABEL_DEFAULT: self.root_node }

    def to_list(self):
        if isinstance(self.root_node, DataTree):
            self.root_node = self.__list__(self.root_node.root_node)
        elif isinstance(self.root_node, dict):
            return [ (i, v) for i,v in self.root_node.items() ]
        elif isinstance(self.root_node, tuple):
            return list(self.root_node)
        elif isinstance(self.root_node, list):
            return self.root_node
        return [ self.root_node ]

    def to_tuple(self):
        if isinstance(self.root_node, DataTree):
            self.root_node = self.__tuple__(self.root_node.root_node)
        elif isinstance(self.root_node, dict):
            return tuple( (i, v) for i,v in self.root_node.items() )
        elif isinstance(self.root_node, (tuple, set, frozenset)):
            return tuple(self.root_node)
        elif isinstance(self.root_node, list):
            return tuple(self.root_node)
        return (self.root_node, )

    def to_sequence(self):
        if isinstance(self.root_node, DataTree):
            self.root_node = self.__dict__(self.root_node.root_node)
        elif isinstance(self.root_node, (dict, list, tuple, set, frozenset)):
            return self.root_node
        return [ self.root_node ]

    def json_custom_serializer(self, obj):
        if isinstance(obj, bytes):
            return {self.__class__.SERIALIZE_KEY_TYPE: 'bytes', 
                    self.__class__.SERIALIZE_KEY_VALUE: base64.b64encode(obj).decode(encoding=self.file_encoding)}

        if isinstance(obj, bytearray):
            return {self.__class__.SERIALIZE_KEY_TYPE: 'bytearray',
                    self.__class__.SERIALIZE_KEY_VALUE: base64.b64encode(bytes(obj)).decode(encoding=self.file_encoding)}

        raise TypeError('Object of type %s is not JSON serializable' % (type(obj).__name__, ) )

    def json_custom_object_hook(self, obj):
        if isinstance(obj, dict) and self.__class__.SERIALIZE_DICT_KEYS.issubset(obj):
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'bytes':
                return base64.b64decode(obj[self.__class__.SERIALIZE_KEY_VALUE].encode(encoding=self.file_encoding))
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'bytearray':
                return bytearray(base64.b64decode(obj[self.__class__.SERIALIZE_KEY_VALUE].encode(encoding=self.file_encoding)))
        return obj

    def encode_byte_dict_key(self, key, sep1='::', sep2='__', avoid_eq_in_key=False):
        if isinstance(key, (tuple, frozenset)):
            return (sep1+self.__class__.__name__+sep1+sep2+type(key).__name__+sep2+sep1
                    +json.dumps([self.encode_bytes_base64(i) for i in key], default=self.json_custom_serializer))
        if avoid_eq_in_key:
            if isinstance(key, bytes):
                return (sep1+self.__class__.__name__+sep1+sep2+type(key).__name__+sep2+sep1
                        +base64.b64encode(key).decode(encoding=self.file_encoding).replace("=","@"))
            return key
            
        if isinstance(key, bytes):
            return (sep1+self.__class__.__name__+sep1+sep2+type(key).__name__+sep2+sep1
                    +base64.b64encode(key).decode(encoding=self.file_encoding))
        return key

    def decode_byte_dict_key(self, key, sep1='::', sep2='__', avoid_eq_in_key=False):
        if not isinstance(key, str):
            if avoid_eq_in_key:
                return key
            return key

        type_hdr_b = sep1+self.__class__.__name__+sep1+sep2+'bytes'+sep2+sep1
        if key.startswith(type_hdr_b) or key.startswith(type_hdr_b.lower()) :
            if avoid_eq_in_key:
                return base64.b64decode(key[len(type_hdr_b):].replace("@","=").encode(encoding=self.file_encoding))
            return base64.b64decode(key[len(type_hdr_b):].encode(encoding=self.file_encoding))

        type_hdr_t = sep1+self.__class__.__name__+sep1+sep2+'tuple'+sep2+sep1
        if key.startswith(type_hdr_t) or key.startswith(type_hdr_t.lower()) :
            return tuple(json.loads(key[len(type_hdr_b):].encode(encoding=self.file_encoding),
                                    object_hook=self.json_custom_object_hook))
        
        type_hdr_f = sep1+self.__class__.__name__+sep1+sep2+'frozenset'+sep2+sep1
        if key.startswith(type_hdr_f) or key.startswith(type_hdr_f.lower()) :
            return frozenset(json.loads(key[len(type_hdr_f):].encode(encoding=self.file_encoding),
                                        object_hook=self.json_custom_object_hook))

        if avoid_eq_in_key:
            return key
        return key
    
    def encode_bytes_base64(self, obj, sep1='::', sep2='__', avoid_eq_in_key=False):

        if isinstance(obj, (bytes, bytearray)):
            return {self.__class__.SERIALIZE_KEY_TYPE: type(obj).__name__,
                    self.__class__.SERIALIZE_KEY_VALUE: base64.b64encode(obj).decode(encoding=self.file_encoding)}

        if isinstance(obj, (tuple, set, frozenset)):
            return {self.__class__.SERIALIZE_KEY_TYPE: type(obj).__name__,
                    self.__class__.SERIALIZE_KEY_VALUE: [ self.encode_bytes_base64(i, sep1=sep1, sep2=sep2,
                                                                                   avoid_eq_in_key=avoid_eq_in_key) for i in obj ]}

        if isinstance(obj, list):
            return [ self.encode_bytes_base64(i, sep1=sep1, sep2=sep2,
                                              avoid_eq_in_key=avoid_eq_in_key) for i in obj ]

        if isinstance(obj, dict):
            return {self.encode_byte_dict_key(k, sep1=sep1, sep2=sep2,
                                              avoid_eq_in_key=avoid_eq_in_key):
                    self.encode_bytes_base64(v, sep1=sep1, sep2=sep2,
                                             avoid_eq_in_key=avoid_eq_in_key) for k,v in obj.items()}

        return obj


    def decode_bytes_base64(self, obj, sep1='::', sep2='__', avoid_eq_in_key=False):

        if isinstance(obj, dict) and self.__class__.SERIALIZE_DICT_KEYS.issubset(obj):
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'bytes':
                return base64.b64decode(obj[self.__class__.SERIALIZE_KEY_VALUE].encode(encoding=self.file_encoding))
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'bytearray':
                return bytearray(base64.b64decode(obj[self.__class__.SERIALIZE_KEY_VALUE].encode(encoding=self.file_encoding)))
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'tuple':
                return tuple([ self.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) 
                               for i in obj[self.__class__.SERIALIZE_KEY_VALUE]])
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'set':
                return set([ self.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) 
                             for i in obj[self.__class__.SERIALIZE_KEY_VALUE]])
            if obj[self.__class__.SERIALIZE_KEY_TYPE] == 'frozenset':
                return frozenset([ self.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) 
                                   for i in obj[self.__class__.SERIALIZE_KEY_VALUE]])
            
        if isinstance(obj, list):
            return [ self.decode_bytes_base64(i, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) for i in obj ]

        if isinstance(obj, dict):
            return {self.decode_byte_dict_key(k, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key):
                    self.decode_bytes_base64(v, sep1=sep1, sep2=sep2, avoid_eq_in_key=avoid_eq_in_key) for k,v in obj.items()}

        return obj

    def flatten_dict(self, d:dict, parent_key:str='', sep:str='________')->dict:
        items = {}
        for k, v in d.items():
            new_key = ("%s%s%s" % (parent_key, sep, k)) if parent_key else k
            if isinstance(v, dict):
                items.update(self.flatten_dict(v, new_key, sep=sep))
            else:
                items[new_key] = v if isinstance(v, str) else json.dumps(v, default=self.json_custom_serializer) 
        return items

    def unflatten_dict(self, d:dict, sep:str='________')->dict:
        result = {}
        for flat_key, v in d.items():
            keys = flat_key.split(sep)
            current = result
            for part in keys[:-1]:
                current = current.setdefault(part, {})
            try:
                current[keys[-1]] = json.loads(v, object_hook=self.json_custom_object_hook)
            except:
                current[keys[-1]] = v
        return result

    def serialize(self, output_format:str=SERIALIZE_FORMATS[0],
                  parent_obj=None,
                  exclude_keys=None,
                  identifier=None, bulk=False, index=None)->str:
        if exclude_keys is None:
            exclude_keys = []
        
        id_key = identifier if isinstance(identifier,str) and identifier else self.identifier
        exclude_keys = exclude_keys.keys() if isinstance(exclude_keys,dict) else exclude_keys
        s_root_node = self._base.rest_data_tree(obj=self.root_node, keyindexes=exclude_keys)
        if parent_obj is None:
            if bulk:
                p_obj = s_root_node
            else:
                p_obj = { id_key : s_root_node }
        elif isinstance(parent_obj,dict):
            p_obj = {k: v for k, v in parent_obj.items() if k not in exclude_keys}
            p_obj[id_key] = s_root_node
        elif isinstance(parent_obj,(list,tuple,set,frozenset)):
            p_list = [ ( None if idx in exclude_keys else v ) for idx,v in enumerate(parent_obj) ] 
            if isinstance(index,int):
                if  index >= len(p_list):
                    p_list += (index+1-len(p_list))*[None]
                p_list[index] = s_root_node
            if bulk:
                p_obj = type(parent_obj)(p_list)
            else:
                p_obj = {id_key : type(parent_obj)(p_list) }
        else:
            raise ValueError("[%s.%s:%d] parent_obj : Invalid Type: (%s : shoule be dict|list|tuple)\n"
                             % (self.__class__.__name__, inspect.currentframe().f_code.co_name,
                                inspect.currentframe().f_lineno, type(parent_obj).__name__))

        if output_format.endswith(('json', 'JSON')):
            return json.dumps(self.encode_bytes_base64(p_obj),
                              indent=self.json_indent, default=self.json_custom_serializer)

        if output_format.endswith(('yaml', 'yml', 'YAML', 'YML')):
            return yaml.dump(self.encode_bytes_base64(p_obj),
                             default_flow_style=self.yaml_default_flow_style)

        if output_format.endswith(('ini', 'INI')):
            sio = io.StringIO()
            if sys.version_info >= (3, 13):
                config = configparser.ConfigParser(allow_unnamed_section=True)
            else:
                config = configparser.ConfigParser()
            config.optionxform = str

            config[id_key] = self.flatten_dict(self.encode_bytes_base64(p_obj, sep1='$$', sep2='%%', avoid_eq_in_key=True))

            config.write(sio)
            content = sio.getvalue()
            sio.close()
            return content

        if output_format.endswith(('toml', 'TOML')):
            return toml.dumps(self.encode_bytes_base64(p_obj), # {self.toml_section : self.encode_bytes_base64(self.root_node)},
                              encoder=self.toml_encoder)
        
        raise ValueError("[%s.%s:%d] Unsupported file format: %s\n"
                         % (self.__class__.__name__, inspect.currentframe().f_code.co_name, inspect.currentframe().f_lineno, output_format))


    def load_deserialized(self, content:str, update=True, input_format:str='json', identifier=None, getall=True, index=None):
        
        id_key = identifier if isinstance(identifier,str) and identifier else self.identifier
        
        if input_format.endswith(('json', 'JSON')):
            raw_contents = self.decode_bytes_base64(json.loads(content, object_hook=self.json_custom_object_hook))
        elif input_format.endswith(('yaml', 'yml', 'YAML', 'YML')):
            raw_contents = self.decode_bytes_base64(yaml.safe_load(content))
        elif input_format.endswith(('ini', 'INI')):
            if sys.version_info >= (3, 13):
                config = configparser.ConfigParser(allow_unnamed_section=True)
            else:
                config = configparser.ConfigParser()
            config.optionxform = str
            config.read_string(content)
            raw_contents = {}
            
            if id_key in config.sections():
                flaten = dict(config[id_key])
                unflaten = self.unflatten_dict(flaten)
                raw_contents = self.decode_bytes_base64(unflaten,sep1='$$', sep2='%%', avoid_eq_in_key=True)
            else:
                for k in config.sections():
                    flaten = dict(config[k])
                    unflaten = self.unflatten_dict(flaten)
                    raw_contents[k] = self.decode_bytes_base64(unflaten, sep1='$$', sep2='%%', avoid_eq_in_key=True)

        elif input_format.endswith(('toml', 'TOML')):
            raw_contents = self.decode_bytes_base64(toml.loads(content))
        else:
            try:
                raw_contents = self.decode_bytes_base64(json.loads(content, object_hook=self.json_custom_object_hook))
            except:
                try:
                    raw_contents = self.decode_bytes_base64(yaml.safe_load(content))
                except:
                    try:
                        if sys.version_info >= (3, 13):
                            config = configparser.ConfigParser(allow_unnamed_section=True)
                        else:
                            config = configparser.ConfigParser()
                        config.optionxform = str
                        config.read_string(content)
                        raw_contents = {}
                        
                        if self.identifier in config.sections():
                            flaten = dict(config[self.identifier])
                            unflaten = self.unflatten_dict(flaten)
                            raw_contents = self.decode_bytes_base64(unflaten,sep1='$$', sep2='%%', avoid_eq_in_key=True)
                        else:
                            for k in config.sections():
                                flaten = dict(config[k])
                                unflaten = self.unflatten_dict(flaten)
                                raw_contents[k] = self.decode_bytes_base64(unflaten, sep1='$$', sep2='%%', avoid_eq_in_key=True)
                                
                    except:
                        try:
                            raw_contents = self.decode_bytes_base64(toml.loads(content))
                        except:
                            raise ValueError("[%s.%s:%d] Unsupported file format: %s\n"
                                             % (self.__class__.__name__, inspect.currentframe().f_code.co_name,
                                                inspect.currentframe().f_lineno, file_path))

        if getall:
            contents = raw_contents
        else:
            if isinstance(raw_contents, dict):
                contents = raw_contents.get(id_key, raw_contents)
            else:
                contents = raw_contents
                
            if ( isinstance(contents,(list,tuple,set,frozenset))
                 and isinstance(index, int)
                 and index > -1 and index < len(contents) ):
                contents = list(contents)[index] if isinstance(contents, (set, frozenset)) else contents[index]

        if update:
            self.merge(obj=contents, type_override=True)
        else:
            self.set_rootnode(contents)

    def open_compressed(self, f_path:str, mode:str):
        if f_path == '-' or f_path == None or (not f_path):
            x_path = 1 if (isinstance(mode, str) and 'w' in mode ) else 0
            # Standard input of standard output
        else: 
            x_path = f_path
        if f_path.endswith('.bz2'):
            return bz2.open(x_path, mode, encoding=self.file_encoding)
        if f_path.endswith('.gz'):
            return gzip.open(x_path, mode, encoding=self.file_encoding)
        if f_path.endswith('.xz'):
            return lzma.open(x_path, mode, encoding=self.file_encoding)

        return open(x_path, mode, encoding=self.file_encoding)

    @classmethod
    def path_format_extsplit(cls, path):
        bn0,ext0 = os.path.splitext(path)
        bn1,ext1,ext0 = (os.path.splitext(bn0)+(ext0, )) if ext0 in cls.COMPRESS_EXT else (os.path.splitext(path)+('', ))
        bn,ext   = (bn1,ext1) if ext1[1:] in cls.SERIALIZE_FORMATS else (bn1+ext1, '')
        return (bn,
                ext[1:]  if ext.startswith('.')  else ext,
                ext0[1:] if ext0.startswith('.') else ext0)

    @classmethod
    def path_format_addext(cls, path, fmt=None, compress=None):
        bn,fext,cext = cls.path_format_extsplit(path)
        if compress is None:
            ext2 = ('.'+cext) if cext and (not cext.startswith('.')) else cext 
        elif isinstance(compress, str) and compress:
            ext2 = compress if compress.startswith('.') else '.'+compress
            if not ext2 in cls.COMPRESS_EXT:
                raise ValueError("[%s.%s:%d] Unknown compress format :%s (Must be one of %s) \n"
                                 % (cls.__name__, inspect.currentframe().f_code.co_name, 
                                    inspect.currentframe().f_lineno, compress, ','.join(cls.COMPRESS_EXT)))
        elif isinstance(compress,bool) and compress:
            if cext:
                ext2 = cext if cext.startswith('.') else ('.'+cext)
            else:
                ext2 = cls.COMPRESS_EXT[0]
        else:
            ext2 = ''
        
        if fmt is None:
            ext1 = fext if fext.startswith('.') else ('.'+fext)
        elif isinstance(fmt, str):
            ext1 = fmt if fmt.startswith('.') else '.'+fmt
        if not ext1[1:] in cls.SERIALIZE_FORMATS:
            raise ValueError("[%s.%s:%d] Unknown compress format :%s (Must be one of %s) \n"
                             % (cls.__name__, inspect.currentframe().f_code.co_name, 
                                inspect.currentframe().f_lineno, ext1[1:], ','.join(cls.SERIALIZE_FORMATS)))
        # print("            : ", bn, fext, cext)
        return bn+ext1+ext2


    def save_serialized(self, file_path:str,
                        parent_obj:dict={}, identifier=None,
                        exclude_keys=None, 
                        bulk=False, index=None,
                        f_perm=0o644, make_directory:bool=True,
                        d_perm=0o755, verbose=False):

        if exclude_keys is None:
            exclude_keys = []
        if file_path in ['-', '1', '2'] or file_path == None or (not file_path):
            flg_stdout = True
            fmt = self.__class__.SERIALIZE_FORMATS[0]
        else:
            flg_stdout = False
            bn,ext = os.path.splitext(file_path)
            if ext.lower() in self.__class__.COMPRESS_EXT:
                bn, ext = os.path.splitext(bn)
            fmt = ext[1:]
        
        content = self.serialize(output_format=fmt, parent_obj=parent_obj, 
                                 identifier=identifier, exclude_keys=exclude_keys,
                                 bulk=bulk, index=index)

        if flg_stdout:
            sys.stdout.write(content)
            return

        if make_directory and os.path.dirname(file_path):
            os.makedirs(os.path.dirname(file_path), mode=d_perm, exist_ok=True)

        with self.open_compressed(file_path, 'wt') as f:
            f.write(content)
        os.chmod(file_path, f_perm)


    def read_serialized(self, file_path:str, update=True, identifier=None, getall=True, index=None, verbose=False):

        content = {}
        if file_path in ['-', '0'] or file_path == None or (not file_path):
            content = sys.stdin.read()
            fmt = "txt"
        else:
            with self.open_compressed(file_path, mode='rt') as f:
                content = f.read()

            bn,ext = os.path.splitext(file_path)
            if ext.lower() in self.__class__.COMPRESS_EXT:
                bn, ext = os.path.splitext(bn)
            fmt = ext[1:]

        id_key = identifier if isinstance(identifier,str) and identifier else self.identifier

        self.load_deserialized(content=content, update=update, input_format=fmt,
                               identifier=id_key, getall=getall, index=index)
