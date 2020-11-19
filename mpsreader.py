#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 17 16:38:53 2020

@author: xueyushi
"""




def load_mps(path):
    """
        MPS format: http://lpsolve.sourceforge.net/5.0/mps-format.htm
        Current Function:
            - not include Semi-continuous
            - not include ranges
    """
    ins = { 'Name': None, 'Var': {}, 'Cons': {}}
    MODE = ['ROWS', 'COLUMNS', 'RHS', 'BOUNDS']
    mode = None
    integral_marker = 0
    obj_marker = 0
    with open(path, 'r') as reader:
        for line in reader:
            line = line.strip().split()
            line = [x.strip() for x in line]

            if not line: continue
            if line[0] == "ENDATA": break
            if line[0] == "NAME":
                ins['Name'] = line[1]
            elif line[0] in MODE and len(line) == 1:
                mode = line[0]
            elif mode == 'ROWS':
                ins['Cons'][line[1]] = {'order': -1, 'type': line[0], 'coef': {}, 'rhs': None}
                if line[0] == 'N':
                    obj_marker = 1
                else:
                    ins['Cons'][line[1]]['order'] = len(ins['Cons']) - 1 - obj_marker
            elif mode == 'COLUMNS':
                # integeral maker
                if len(line) > 1 and line[1] == "'MARKER'":
                    if line[2] == "'INTORG'":
                        integral_marker = 1
                    elif line[2] == "'INTEND'":
                        integral_marker = 0
                    else:
                        raise Exception("Unknown Maker.")
                    continue

                var = line[0]
                if var not in ins['Var']:
                    ins['Var'][var] = {'order': len(ins['Var']), 'type': integral_marker, 'ub': float('inf'), 'lb': 0}
                for i in range(1, len(line), 2):
                    ins['Cons'][line[i]]['coef'][var] = float(line[i+1])
            elif mode == 'RHS':
                for i in range(1, len(line), 2):
                    ins['Cons'][line[i]]['rhs'] = float(line[i+1])
            elif mode == 'BOUNDS':
                if line[0] == 'UP':
                    ins['Var'][line[2]]['ub'] = float(line[-1])
                elif line[0] == 'LO':
                    ins['Var'][line[2]]['lb'] = float(line[-1])
                elif line[0] == 'FX':
                    ins['Var'][line[2]]['ub'] = float(line[-1])
                    ins['Var'][line[2]]['lb'] = float(line[-1])
                elif line[0] == 'FR':
                    ins['Var'][line[2]]['lb'] = -float('inf')
                elif line[0] == 'MI':
                    ins['Var'][line[2]]['ub'] = 0
                    ins['Var'][line[2]]['lb'] = -float('inf')
                elif line[0] == 'BV':
                    ins['Var'][line[2]]['type'] = 2
                    ins['Var'][line[2]]['lb'] = 0
                    ins['Var'][line[2]]['ub'] = 1
                elif line[0] == 'UI':
                    ins['Var'][line[2]]['type'] = 1
                    ins['Var'][line[2]]['ub'] = int(float(line[-1]))
                elif line[0] == 'LI':
                    ins['Var'][line[2]]['type'] = 1
                    ins['Var'][line[2]]['lb'] = int(float(line[-1]))
                else:
                    raise Exception("Unkonwn Types in Bounds.")
            else:
                raise Exception("Unknown Mode.")


    # rows
    for key, row in ins['Cons'].items():
        if row['type'] != 'N' and 'rhs' not in row:
            row['rhs'] = 0

    # variables
    for key, var in ins['Var'].items():
        if var['type'] == 1 and var['lb'] == 0 and var['ub'] == 1:
            var['type'] == 2


    return ins



def parse_aux(path):
    ll_ins = {'N': 0, 'M': 0, 'LC': [], 'LR': [], 'LO': [], 'OS': 1, 'IC': [], 'IB': None, 'Interdiction': False}
    with open(path, 'r') as reader:
        num_line = 0
        for line in reader:
            line = line.strip()
            if not line: continue
            line = [x.strip() for x in line.split()]

            if num_line == 0:
                ll_ins['N'] = int(line[1])
            elif num_line == 1:
                ll_ins['M'] = int(line[1])
            elif line[0] in ['LC', 'LR']:
                ll_ins[line[0]].append(int(line[1]))
            elif line[0] in ['IC', 'LO']:
                ll_ins[line[0]].append(float(line[1]))
            elif line[0] == 'OS':
                ll_ins['OS'] = int(line[1])
            elif line[0] == 'IB':
                ll_ins['IB'] = float(line[1])
            else:
                raise Exception("Unknow Mode.")

            num_line += 1

    if ll_ins['IC']:
        ll_ins['Interdiction'] = True

    return ll_ins


def load_mibs(mps_file, aux_file):
    ins = load_mps(mps_file)
    ll_ins = parse_aux(aux_file)


    # var order, 
    n = len(ins['Var'])
    var = [0] * n
    for key, val in ins['Var'].items():
        index = val['order']
        var[index] = val
        var[index]['name'] = key

    # constraints
    m = len(ins['Cons'])
    cons = [0] * m
    for key, val in ins['Cons'].items():
        index = val['order']
        coef = [0] * n
        for var_name, var_coef in val['coef'].items():
            var_index = ins['Var'][var_name]['order']
            coef[var_index] = var_coef

        
        cons[index] = {'type': val['type'], 'coef': coef, 'rhs': val['rhs']}


    return {'model': {'Var': var, 'Cons': cons}, 'aux': ll_ins}

def mibp_stats(mps_file, aux_file):
    ins = load_mibs(mps_file, aux_file)

    stats = {'Interdiction': ins['aux']['Interdiction'], 'upper': {}, 'lower': {}}

    if ins['aux']['Interdiction'] == True:
        n = ins['aux']['N']
        m = ins['aux']['M']
        stats['upper'] = {'Var': n, 'Con': 1, 'VarType': set([2])}
        stats['lower'] = {'Var': n, 'Con': m, 'VarType': set([2])}
    else:
        n = len(ins['model']['Var'])
        m = len(ins['model']['Cons']) - 1

        # variable type
        stats['upper'] = {'Var': n - ins['aux']['N'], 'Con': m - ins['aux']['M'], 'VarType': set()}
        stats['lower'] = {'Var': ins['aux']['N'], 'Con': ins['aux']['M'], 'VarType': set()}

        for i in range(n):
            if i in ins['aux']['LC']:
                stats['lower']['VarType'].add( ins['model']['Var'][i]['type'])
            else:
                stats['upper']['VarType'].add( ins['model']['Var'][i]['type'])
    
    return {'Interdiction': ins['aux']['Interdiction'], 'UpperVar': stats['upper']['Var'], 'LowerVar': stats['lower']['Var'], 'UpperCon': stats['upper']['Con'], 'LowerCon': stats['lower']['Con'], 'UpperType': stats['upper']['VarType'], 'LowerType': stats['lower']['VarType']}
    # return {'Interdiction': ins['aux']['Interdiction'], 'Var': [stats['upper']['Var'], stats['lower']['Var']], 'Con': [stats['upper']['Con'], stats['lower']['Con']], 'VarType': [stats['upper']['VarType'], stats['lower']['VarType']] }




