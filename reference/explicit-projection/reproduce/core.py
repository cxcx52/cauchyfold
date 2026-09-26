"""Deterministic CFdagger v2 Profile I k=16 derivation. No benchmarks.

Normal invocation regenerates all formula-derived artifacts. Estimator attacks are
run by the separately pinned runner; no stale result is silently relabelled.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import subprocess
from math import isqrt, log2
from pathlib import Path
import sys

sys.set_int_max_str_digits(0)
ROOT = Path(__file__).resolve().parent

def canonical(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')

def put(name, obj):
    p=ROOT/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(canonical(obj))

def md(name, text):
    (ROOT/name).write_bytes((text.rstrip()+'\n').encode('utf-8'))

def load(name): return json.loads((ROOT/name).read_bytes())
def ceildiv(a,b): return -(-a//b)
def ceilroot(a): return isqrt(a)+(isqrt(a)**2<a)
def frac(x): return {'numerator':str(x.numerator),'denominator':str(x.denominator)}
def exponent(x): return log2(x.denominator)-log2(x.numerator)

def validate_compiler(p,c):
    """Check numerical manifest invariants; never manufacture a compiler result."""
    import jsonschema
    jsonschema.Draft202012Validator(load('compiler_manifest.schema.json')).validate(c)
    assert c['arity']==16 and c['profile']=='I'
    assert c['parameter_id']==p['parameter_id']
    assert c['parameter_file_sha256']==hashlib.sha256((ROOT/'parameters.json').read_bytes()).hexdigest()
    if c['status']!='COMPLETE':
        assert all(v is None for v in c['resolved_dimensions'].values())
        return
    assert not c['unresolved_fields'] and all(v is True for v in c['checks'].values())
    sem=c['semantic'];enc=c['encoding'];h=c['handoff'];r1=c['r1cs'];dim=c['resolved_dimensions']
    n,y,r=sem['n'],sem['y'],sem['r'];assert n>=1 and y>=1 and 1<=r<=y
    assert 1+sem['public_input_K_coordinates']<=n
    rawbits={'A_st':192*(n+y),'A_H':3072*r,'A_aux':192*enc['auxiliary_gate_K_values']+enc['auxiliary_scalar_bits']}
    counts={'A_st':0,'A_H':0,'A_aux':0};intervals=[]
    expected_segments={'accumulator_state':('A_st','input'),
        **{f'fresh_state_{i:02}':('A_st','input') for i in range(1,17)},
        'folded_output_state':('A_st','post_cauchy_pre_field'),
        'carrier':('A_H','pre_cauchy'),'field_auxiliary':('A_aux','post_cauchy_pre_field')}
    assert len({s['segment_id'] for s in enc['segments']})==20
    assert {s['segment_id'] for s in enc['segments']}==set(expected_segments)
    for s in enc['segments']:
        mid=s['matrix_id'];counts[mid]+=1;L=rawbits[mid];C=ceildiv(L,64)
        assert (mid,s['commitment_phase'])==expected_segments[s['segment_id']]
        assert s['encoded_bits']==L and s['matrix_columns']==C
        assert s['zero_padding_coefficients']==64*C-L
        assert s['honest_squared_norm_bound']==L
        intervals.append((s['start_coefficient'],s['start_coefficient']+64*C))
        assert (ROOT/s['source_bit_mapping_artifact']).is_file()
    assert counts=={'A_st':18,'A_H':1,'A_aux':1}
    for key,mid in [('state','A_st'),('carrier','A_H'),('auxiliary','A_aux')]:
        assert dim[key+'_ring_columns']==ceildiv(rawbits[mid],64)
        assert dim[key+'_honest_opening_bound_squared']==rawbits[mid]
    assert dim['semantic_dimension_n']==n and dim['residual_dimension_y']==y and dim['bilinear_image_dimension_r']==r
    intervals.sort();assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
    N=p['backend']['handoff_capacity_coefficients'];one=h['fixed_one_coordinate_index']
    assert 0<=one<N and all(0<=a<b<=N and not a<=one<b for a,b in intervals)
    zeroranges=sorted(tuple(x) for x in h['fixed_zero_coordinate_ranges']);P0=sum(b-a for a,b in zeroranges)
    assert all(0<=a<b<=N and not a<=one<b for a,b in zeroranges)
    assert all(a[1]<=b[0] for a,b in zip(zeroranges,zeroranges[1:]))
    # Every coefficient is either an encoded bit, a fixed zero, or constant 1.
    bits=[(s['start_coefficient'],s['start_coefficient']+s['encoded_bits']) for s in enc['segments'] if s['encoded_bits']]
    partition=sorted(bits+zeroranges+[(one,one+1)])
    assert partition[0][0]==0 and partition[-1][1]==N
    assert all(a[1]==b[0] for a,b in zip(partition,partition[1:]))
    assert h['fixed_zero_coordinates_count']==P0==dim['fixed_zero_coordinates_count']
    assert h['linear_rows_before_backend_padding']==40973+P0
    assert h['linear_rows_after_backend_padding']==40973+P0+320
    assert h['unpadded_coefficients_including_segment_padding_and_constant']==sum(b-a for a,b in intervals)+1<=N
    ell=r1['sumcheck_rounds'];assert 0<=ell<=30 and r1['constraint_count_padded']==2**ell
    assert 0<r1['constraint_count_unpadded']<=2**ell and dim['sumcheck_rounds']==ell
    assert ell==(r1['constraint_count_unpadded']-1).bit_length()
    assert r1['shape_independent_of_c'] is True
    assert {m['matrix'] for m in r1['matrix_artifacts']}=={'A','B','C'}
    for m in r1['matrix_artifacts']:
        assert hashlib.sha256((ROOT/m['path']).read_bytes()).hexdigest()==m['sha256']
    assert (ROOT/r1['wire_to_bit_coordinate_map_artifact']).is_file()
    for op in c['operation_counts']:
        assert (ROOT/op['derivation_artifact']).is_file()
    for obj,pathkey,hashkey in [(sem,'relation_Q_artifact','relation_Q_sha256'),(sem,'basis_U_artifact','basis_U_sha256'),(sem,'left_inverse_J_artifact','left_inverse_J_sha256'),(c['compiler'],'path','sha256')]:
        data=(ROOT/obj[pathkey]).read_bytes();assert hashlib.sha256(data).hexdigest()==obj[hashkey]

def build_layers(p):
    b=p['backend']; f=p['field']; q=f['q'];d=f['ring_degree'];rho=b['radix'];dig=b['digit_count']
    assert rho**(dig-1)<q<=rho**dig
    M=5**d; T=2*d;mu=2*d;sig=b['sigma'];a=b['main_rank'];tau=b['tau']
    N=b['handoff_capacity_coefficients']; S=b['honest_initial_norm_squared_bound']; out=[]
    for i,s in enumerate(b['blocks']):
        n=ceildiv(N,d*s);Npad=d*s*n;terminal=i==len(b['blocks'])-1
        G=ceildiv(2*mu*S*M,M-1) if terminal else 2*mu*S
        x={'level':i,'raw_source_coefficients':N,'padded_source_coefficients':Npad,'padding':Npad-N,
           'blocks':s,'block_length_ring':n,'S':S,'sigma':sig,'G':G,'terminal':terminal}
        assert q*q>=128**2*sig**2*S
        if terminal:
            ep=0
            while b['pivot_radix']**ep<q:ep+=1
            x.update(A_kernel_radius=ceilroot(64*T*T*G),
                pivot_kernel_radius=ceilroot(b['pivot_radix']**2*d*a*ep),
                terminal_ring_field_coefficients_without_response=(s-1)*a*d+b['pivot_rank']*d+tau*(d*s*(s+1)//2-1),
                terminal_response_coefficients=d*n)
        else:
            Lt=dig*a*s;Lh=dig*tau*s*(s+1)//2;Nz=d*n;bd=rho//2
            Schild=Nz*bd**2+ceildiv(2*G+2*Nz*bd**2,rho**2)+d*(Lt+Lh)*bd**2
            Nchild=2*Nz+d*(Lt+Lh)
            x.update(child_raw_coefficients=Nchild,child_S=Schild,Lt_ring=Lt,Lh_ring=Lh,
                A_kernel_radius=ceilroot(64*T*T*(1+rho**2)*sig**2*Schild),
                B_D_kernel_radius=ceilroot(4*sig**2*Schild))
            N=Nchild;S=Schild
        out.append(x)
    original=load('expected_schedule.json')['layers']
    assert out==original, 'Selected v2 schedule changed: do not silently reuse ledger.'
    return out

def registry(p,layers,c):
    q=p['field']['q'];d=p['field']['ring_degree'];b=p['backend'];f=p['front_end']
    sig=b['sigma'];N=b['handoff_capacity_coefficients'];beta0=ceilroot(4*sig**2*b['honest_initial_norm_squared_bound'])
    roles=[]
    def add(mid,logical,rows,cols,hon,weak,beta,formula,source,**extra):
        roles.append({'matrix_id':mid,'role_id':mid,'logical_role_ids':logical,'q':q,'d':d,'rows':rows,'columns':cols,
          'norm_model':'coefficient_l2','honest_opening_bound_squared':hon,'extracted_opening_bound_squared':weak,
          'kernel_radius_beta':beta,'beta_formula':formula,'formula_source':source,
          'random_matrix_distribution':'independent_uniform_Rq_matrix_except_uses_of_same_matrix_id',
          'shared_random_matrix':len(logical)>1,'status':'READY' if cols is not None else 'UNRESOLVED_COMPILER_COLUMNS',**extra})
    # The only uninstantiated data are actual compiler-dependent lengths.
    dims=c.get('resolved_dimensions',{})
    for typ,logical,rankkey,colformula,bitformula in [
      ('state',['state/accumulator']+[f'state/fresh/{i}' for i in range(16)]+['state/output'],'state_commitment_rank','3*(n+y)','192*(n+y)'),
      ('carrier',['carrier/pre_cauchy'],'carrier_commitment_rank','48*r','3072*r'),
      ('auxiliary',['field/auxiliary'],'auxiliary_commitment_rank','ceil((192*g_K+h_aux)/64)','192*g_K+h_aux')]:
        add('frontend_'+typ,logical,f[rankkey],dims.get(typ+'_ring_columns'),dims.get(typ+'_honest_opening_bound_squared'),sig**2*N,
            beta0,'ceil(sqrt(4*sigma0^2*S0))','v2 §§10.5,11.2,24; state sharing §§1.1,1.3,10.1',
            columns_formula=colformula,honest_bound_squared_formula=bitformula,
            protocol_matrix_symbol={'state':'A_st','carrier':'A_H','auxiliary':'A_aux'}[typ],
            rank_origin='new_explicit_concrete_v1_selection',unresolved_fields=['columns','honest_opening_bound_squared'] if dims.get(typ+'_ring_columns') is None else [],
            conservative_honest_opening_bound_squared_if_compiler_fits=N,
            chronology={'state':'sources before c; output after c, before field randomness','carrier':'before c','auxiliary':'after c, before field randomness'}[typ])
    for x in layers:
        i=x['level'];a=b['main_rank'];T=p['short_challenge']['operator_norm_bound']
        add(f'backend_{i}_A',[f'linear/{i}/A'],a,x['block_length_ring'],x['S'],sig**2*x['S'],x['A_kernel_radius'],
            'ceil(sqrt(64*Bop^2*G))' if x['terminal'] else 'ceil(sqrt(64*Bop^2*(1+rho^2)*sigma_next^2*S_next))',
            'v2 (19.4)' if x['terminal'] else 'v2 (6.7)-(6.9)',level=i,
            honest_bound_scope='Per-block upper bound inherited from total source norm; not simultaneous equality for each block.')
        if x['terminal']:
            ep=0
            while b['pivot_radix']**ep<q:ep+=1
            E=d*a*ep*(b['pivot_radix']//2)**2
            add(f'backend_{i}_pivot',[f'linear/{i}/pivot'],b['pivot_rank'],a*ep,E,E,x['pivot_kernel_radius'],
                'ceil(sqrt(rho_p^2*d*a*ell_p))','v2 (19.3)',level=i)
        else:
            for typ,rankkey,L in [('B','auxiliary_B_rank',x['Lt_ring']),('D','auxiliary_D_rank',x['Lh_ring'])]:
                add(f'backend_{i}_{typ}',[f'linear/{i}/{typ}'],b[rankkey],L,d*L*(b['radix']//2)**2,sig**2*x['child_S'],x['B_D_kernel_radius'],
                    'ceil(sqrt(4*sigma_next^2*S_next))','v2 (6.7)-(6.9)',level=i)
    assert len(roles)==20 and len({x['matrix_id'] for x in roles})==20
    assert sum(x['status']=='READY' for x in roles)==17 or c.get('status')=='COMPLETE'
    assert all(x['kernel_radius_beta']<q for x in roles)
    return {'protocol':p['protocol'],'profile':'I','k':16,'parameter_id':p['parameter_id'],
      'independent_matrix_count':20,'backend_matrix_count':17,'front_end_matrix_count':3,
      'protocol_symbol_to_matrix_id':{'A_st':'frontend_state','A_H':'frontend_carrier','A_aux':'frontend_auxiliary'},
      'independent_role_enumeration_complete':True,'numerical_instantiation_complete':all(x['status']=='READY' for x in roles),
      'scope':'Nondegenerate r>=1; exactly three front matrices; source/output share A_st. Repeated commitments do not repeat an MSIS assumption.',
      'logical_state_commitment_uses':18,'roles':roles,
      'unresolved_dependencies':['Actual CFdagger front-end compiler and relation manifest'] if any(x['status']!='READY' for x in roles) else []}

def statistics(p,layers,c):
    q=p['field']['q'];K=q**4;b=p['backend'];M=5**64
    ell=c.get('resolved_dimensions',{}).get('sumcheck_rounds')
    cap=p['compiler_contract']['field_sumcheck_round_cap'];ellused=ell if ell is not None else cap
    assert ellused<=cap
    theta=Fraction(7,8)+Fraction(1,2**1000)
    one=theta*Fraction(3*b['sigma']**2,3*b['sigma']**2-1)
    projection=one**b['projection_rows']; assert projection<=Fraction(1,2**140)
    field=Fraction(4*ellused,K);cauchy=Fraction(32,K-16)
    terms=[];total=field+cauchy;coarse=field+cauchy
    for x in layers:
        s=x['blocks'];support=Fraction(1,M-1)+Fraction(s-1,M) if x['terminal'] else Fraction(s,M)
        co=3*b['response_retry_cap']*support;agg=Fraction(1,q**b['tau']);proj=b['projection_retry_cap']*projection
        total+=proj+agg+co;coarse+=Fraction(b['projection_retry_cap'],2**140)+agg+co
        terms.append({'level':x['level'],'projection_error_reference':'projection_certificate.bound_per_attempt',
          'projection_union_multiplier':b['projection_retry_cap'],'aggregation_error_bound':frac(agg),
          'coordinate_forking_error_bound':frac(co),'coordinate_support_sizes':[str(M-1 if x['terminal'] and j==0 else M) for j in range(s)]})
    assert total<=coarse<=Fraction(1,2**128)
    comp=sum((Fraction(1,2**b['projection_retry_cap'])+Fraction(1,2**b['response_retry_cap']) for x in layers),Fraction())
    assert comp<Fraction(1,2**156)
    stat={'profile':'I','k':16,'classification':'COMPUTED_EXACT_RATIONAL_BOUND',
      'conditions':['Compiler capacity and actual field-round invariants checked in compiler_manifest.json.','Exact independent public-coin sampling and checkpoint/retry grammar of CFdagger v2.'],
      'field_rounds_actual':ell,'field_round_cap':cap,'field_term_uses':'actual_rounds' if ell is not None else 'public_cap_not_measured_circuit',
      'field_error_upper_bound':frac(field),'actual_field_error_bound_formula':'4*ell_F/q^4',
      'cauchy_error_upper_bound':frac(cauchy),'projection_certificate':{
        'source':'v2 (12.1)-(12.2)','theta':frac(theta),'bound_per_attempt':{
            'base':frac(one),'exponent':b['projection_rows']},'le_2_minus_140_verified_exactly':True,
        'norm_assumption':'q^2>=128^2*sigma^2*S, all 6 levels checked'},
      'layers':terms,'base_statistical_term':{'meaning':'Profile I has no seeded/PRG compilation term','equal_to_total_statistical_term':True},
      'total_statistical_term':{'type':'upper_bound_on_kappa_alg','rational':frac(total),
        'negative_log2_upper_bound_display':exponent(total),'display_is_computational_security_bits':False},
      'coarser_certificate_using_2_minus_140':frac(coarse),'total_le_2_minus_128_exact':True,
      'computational_assumption':{'type':'role_specific_Module_SIS','number_of_independent_matrices':20,
        'included_in_statistical_term':False,'advantage_formula':'sum_j Adv_MSIS(theta_j,B+S_j), plus P/B and finite-bit Setup coupling if used'},
      'node_computational_security_certified':False}
    completeness={'profile':'I','classification':'COMPUTED_EXACT_RATIONAL_UPPER_BOUND','layers':len(layers),
      'per_layer_projection_exhaustion_bound':frac(Fraction(1,2**b['projection_retry_cap'])),
      'per_layer_response_exhaustion_bound':frac(Fraction(1,2**b['response_retry_cap'])),
      'base_statistical_term':frac(comp),'total_statistical_term':frac(comp),
      'total_completeness_error_lt_2_minus_156':True,'negative_log2_upper_bound_display':exponent(comp),
      'computational_assumption_required_for_this_bound':False,
      'conditions':['Legal honest input','compiler/encoding correctness','exact independent randomness','payload-free retries before child submission'],
      'scope':'Protocol retry failure; excludes Setup sampling abort, transport faults and implementation errors.'}
    return stat,completeness

def generate_inputs(p,reg):
    for role in reg['roles']:
        ready=role['columns'] is not None
        x={'matrix_id':role['matrix_id'],'role_ids':role['logical_role_ids'],'q':role['q'],'d':role['d'],
          'rows':role['rows'],'columns':role['columns'],'beta':role['kernel_radius_beta'],'norm_model':role['norm_model'],
          'expanded_sis':{'n':role['d']*role['rows'],'m':None if not ready else role['d']*role['columns'],
            'norm':2,'length_bound':role['kernel_radius_beta']},'status':'READY' if ready else 'UNRESOLVED_COMPILER_DIMENSIONS',
          'estimator_commit':p['security']['estimator_commit'],
          'interpretation':'Generic q-ary lattice attacks on coefficient dimensions; structured matrix is NOT iid scalar matrix and structure-specific attacks are not certified absent.'}
        put('estimator_inputs/'+role['matrix_id']+'.json',x)
