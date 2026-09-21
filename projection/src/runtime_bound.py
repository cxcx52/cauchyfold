"""Exact evaluation of the conditional time theorem in declared common units.

Input values must already bound the COMPLETE uniform conditional cost terms.
No honest benchmark times, oracle counts or missing-zero defaults are accepted.
"""
from fractions import Fraction as F


BLOCKS = (9,6,5,4,4,7)


def evaluate(costs):
    required={'H','W','H_F','H_C','W_F','W_C','unit'}
    if set(costs)!=required or not costs['unit']:
        raise ValueError('Supply every conditional bound in one explicit cost unit.')
    H,W=[F(x) for x in costs['H']],[F(x) for x in costs['W']]
    if len(H)!=6 or len(W)!=6:
        raise ValueError('Exactly six layer bounds required.')
    outer=[F(costs[x]) for x in ('H_F','H_C','W_F','W_C')]
    if min(H+W+outer)<0:
        raise ValueError('Negative cost bound.')
    t=F(0)
    for i in reversed(range(6)):
        t=W[i]+2*160*(1+2*BLOCKS[i])*(H[i]+t)
    hf,hc,wf,wc=outer
    return {'T0':str(t),'Tnode':str(4*t+4*hf+2*hc+2*wf+wc),'unit':costs['unit']}


def check_symbolic_weights():
    weights=[];factor=1
    for i,s in enumerate(BLOCKS):
        before=factor;factor*=2*160*(1+2*s)
        weights.append((before,factor))
    for i in range(6):
        for kind,pos in [('W',0),('H',1)]:
            costs={'H':[0]*6,'W':[0]*6,'H_F':0,'H_C':0,'W_F':0,'W_C':0,'unit':'formal basis coefficient'}
            costs[kind][i]=1
            got=evaluate(costs)
            assert F(got['Tnode'])==4*weights[i][pos]
    return {'status':'PASS','formal_basis_cases':12,'numeric_prover_costs_assumed':False}
