"""Emit explicit layouts, source provenance, component status and fresh tests."""
from pathlib import Path
import hashlib,json,math,struct,time
from compression import NormCodec,BitWriter,concrete_field_certificate
from profile import ROOT,Q,build,dump

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for x in iter(lambda:f.read(1<<20),b''):h.update(x)
    return h.hexdigest()

def run():
    p=build();k=p['k'];V=p['values'];B=192*V;segments=[]
    for s in range(k+2):
        segments.append(dict(name='accumulator' if s==0 else ('output' if s==k+1 else f'fresh_{s}'),
            start=192*73*s,length=192*73,matrix='A_st',ring_columns=219,
            commitment_phase='post_cauchy_pre_field' if s==k+1 else 'public_input'))
    hstart=192*73*(k+2);astart=hstart+192*4*k
    segments.extend([dict(name='carrier',start=hstart,length=192*4*k,matrix='A_H',ring_columns=12*k,commitment_phase='pre_cauchy'),
      dict(name='auxiliary',start=astart,length=192*36+B,matrix='A_aux',ring_columns=231*k+654,commitment_phase='post_cauchy_pre_field')])
    assert segments[-1]['start']+segments[-1]['length']==p['used']-1
    dump(ROOT/'artifacts/encoding-layout.json',dict(k=k,value_order='(k+2) states of 73 K, 4k carrier K, 36 product-gate K',
        segments=segments,constant_coordinate=p['used']-1,reserved_zero_coordinates=0,
        value_bits=192*V,helper_start=B,helper_bits=192*V,bit_order='48 LSB-first bits per Fq coefficient; basis order 1,theta,theta^2,theta^3',
        prefix_helpers='helper[B+192*v+48*t+j]=product_{h=j}^{47} [bit_h == bit_h(q)]; helper e_48 is fixed one',
        backend_partition_padding=p['layers'][0]['padding'],backend_padding_has_explicit_zero_equations=True))
    values=(ROOT/'artifacts/compiler/values.u64').read_bytes()
    def Kval(i):return list(struct.unpack_from('<4Q',values,32*i))
    publics=[dict(state=s,coordinates=[Kval(73*s+j) for j in range(5)]) for s in range(k+2)]
    dump(ROOT/'artifacts/public_statement_fixture.json',dict(status='SYNTHETIC_TEST_INSTANCE_NOT_PRODUCTION',k=k,
        public_coordinates=publics,cauchy_challenge=[k+17,3,4,5],poles=list(range(k)),scales=[1]*k,
        actual_lattice_commitments_included=False))
    dump(ROOT/'artifacts/sparse-matrix-format.json',dict(format='CF1024_RECIPE_CSR_V1',endianness='little',
        matrix_files={n:[n+'.ptr',n+'.ent'] for n in 'ABC'},pointer_type='uint32',entry_type=['uint32 column','uint32 coefficient_recipe'],
        explicit_rows=p['field_rows'],zero_padded_rows=p['field_padded_rows']-p['field_rows'],columns=p['used'],
        key_bits=dict(sign='31',kind='28..30',index='8..27',basis='6..7',bit='0..5'),
        recipe_kinds={'0':'2^bit theta^basis; index=0','1':'public_coordinate[state=index//5][index%5]; basis=bit=0',
          '2':'(c-index)^(-1) * 2^bit theta^basis','3':'(c-index)^(-2) * 2^bit theta^basis',
          '4':'D(c)^(-1) c^index * 2^bit theta^basis'},
        sign_rule='multiply by (-1)^sign',coefficient_public_dependence_only=True,
        note='All CSR row pointers and entries are materialized; recipes specify public challenge-dependent numeric coefficients.'))
    dump(ROOT/'artifacts/initial-operator.json',dict(status='MATHEMATICAL_OPERATOR_SPEC_NOT_FULL_IMPLEMENTED_LATTICE_OPERATOR',
        row_order=['all segment commitment equations, each 64*rank scalar rows','A^T eq_tau, four basis equations',
                   'B^T eq_tau, four basis equations','C^T eq_tau, four basis equations','fixed-one equation','backend alignment zero equations'],
        semantic_segments=len(segments),commitment_scalar_rows=64*32*(k+4),field_terminal_scalar_rows=12,
        fixed_constant_rows=1,padding_zero_rows=p['layers'][0]['padding'],
        total_rows=p['layers'][0]['linear_rows'],
        unimplemented=['full product-setup matrix generation','commitment matrix forward/adjoint routines','full lattice backend replay']))
    tests=[]
    for L in p['layers']:
        items=[('projection',L['projection_codec'])]
        if 'terminal_codec' in L:items.append(('terminal',L['terminal_codec']))
        for kind,d in items:
            c=NormCodec(d['n'],d['T'],'rice',d['k']);assert c.nbytes==d['bytes']
            dense=math.isqrt(d['T']//d['n']);spike=math.isqrt(d['T'])
            vectors=[[0]*c.n,[spike]+[0]*(c.n-1),[-spike]+[0]*(c.n-1),
                     [dense if j%2 else -dense for j in range(c.n)]]
            for a in vectors:
                b=c.encode(a);assert c.decode(b)==a
            # Encode a deliberately over-norm vector without calling the encoder.
            bad=[spike,spike]+[0]*(c.n-2);w=BitWriter(c.nbytes)
            for x in bad:
                u=2*x if x>=0 else -2*x-1;quot,rem=divmod(u,1<<c.k);w.zeros(quot);w.write(1,1);w.write(rem,c.k)
            try:c.decode(bytes(w.data))
            except ValueError: rejected=True
            else:raise AssertionError('over-norm vector was decoded')
            tests.append(dict(layer=L['i'],kind=kind,dimension=c.n,positive_roundtrips=4,over_norm_rejected=rejected))
    dump(ROOT/'evidence/current_parameter_codec_tests.json',dict(status='PASS',cases=tests))
    dump(ROOT/'evidence/field_certificate.json',concrete_field_certificate())
    source_digest='ee6feffa7b469336f23fba33b85dd4b9ef112a5202e8b1416c9b875f9085ef3c'
    dump(ROOT/'evidence/reused_component.json',dict(component='compression.py',sha256=sha(ROOT/'src/compression.py'),
         matches_reference_source=source_digest==sha(ROOT/'src/compression.py')))
    dump(ROOT/'artifacts/matrix-registry.json',dict(registry_version='cf1024-integration-v1',independent_matrix_count=17,
        matrix_distribution='independent uniform Rq matrices; A_st reused across all states counts once',
        source_commitments=k+1,logical_state_uses=k+2,roles=p['roles'],
        actual_keys_generated=False,official_estimator_completed=False,complete_node_certified=False))
    return tests
if __name__=='__main__':print('codec configurations checked:',len(run()))
