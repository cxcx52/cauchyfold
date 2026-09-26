"""Exhaustive finite-grid search using only exact-state merging and safe cost cuts.
This certifies an optimum of this restricted cost grid, NOT an architectural optimum.
The feasibility envelope deliberately retains the original MSIS reference problems.
"""
from model import *
from pathlib import Path

def exact_search(k,radices=(4,8,16,32,64,128),max_depth=5):
    f=front(k,split_aux=True)
    warm=optimize(k,radices,max_depth)
    best=(warm['total_bytes']-f['wrapper_p_bytes']-f['wrapper_v_bytes'],tuple(tuple(x) for x in warm['path']))
    choices=[(s,rho) for s in range(2,33) for rho in radices
             if max(ceildiv(48,rho.bit_length()-1)*A*s,ceildiv(48,rho.bit_length()-1)*TAU*s*(s+1)//2)<=REFERENCE_AUX_B]
    nodes={(f['capacity'],f['used']):Node(f['capacity'],f['used'],0,())}
    layers=[];counts={'generated_transitions':0,'terminal_candidates_costed':0,'identical_state_merges':0}
    # s >= 2: at least one A commitment, one pivot, three symmetric ring entries
    # per aggregation row, minus 3 omitted scalars, plus two accept tags.
    min_terminal=A*384+AP*384+TAU*3*384-TAU*6+2
    for depth in range(max_depth+1):
        print('exact',k,'depth',depth,'states',len(nodes),'best',best[0],flush=True)
        for a in nodes.values():
            for s in range(2,33):
                structural=(s-1)*A*384+AP*384+TAU*s*(s+1)//2*384-TAU*6+2
                if a.cost+structural>=best[0]:break
                if not main_feasible(a.raw,a.S,s):continue
                if ceil_sqrt((8*TOP)**2*terminal_G(a.S))>REFERENCE_MAIN_BETA:continue
                p,v=layer_cost(a.raw,a.S,s,True);counts['terminal_candidates_costed']+=1
                if a.cost+p+v<best[0]:best=(a.cost+p+v,a.path+((s,None),))
        layers.append({'depth':depth,'states':len(nodes),'best_backend_bytes':best[0]})
        if depth==max_depth:break
        nexts={}
        for a in nodes.values():
            for s,rho in choices:
                if not transition_feasible(a.raw,a.S,s,rho):continue
                p,v=layer_cost(a.raw,a.S,s,False)
                cost=a.cost+p+v
                if cost+min_terminal>=best[0]:continue
                raw,S,*_=child(a.raw,a.S,s,rho)
                counts['generated_transitions']+=1
                key=(raw,S)
                old=nexts.get(key)
                if old is None or old.cost>cost:
                    nexts[key]=Node(raw,S,cost,a.path+((s,rho),))
                else:counts['identical_state_merges']+=1
        if not nexts:break
        nodes=nexts
    result=evaluate_schedule(k,list(best[1]),split_aux=True)
    result['search']=dict(algorithm='exhaustive restricted-grid search; exact (raw,S,depth) merging only',
                         radices=radices,max_nonterminal=max_depth,block_count_range=[2,32],
                         counts=counts,levels=layers,
                         result_is_global_protocol_optimum=False)
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('k',type=int,nargs='+'); a=p.parse_args()
    out=Path(__file__).parent/'results'
    for k in a.k:
        r=exact_search(k)
        (out/f'k{k}_exact.json').write_bytes((json.dumps(r,indent=2,sort_keys=True)+'\n').encode('utf-8'))
        print('FINAL',k,r['total_bytes'],r['KiB'],r['path'],flush=True)
