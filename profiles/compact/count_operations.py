"""Typed counts affected by the selected norm and rank parameters."""
import json
from pathlib import Path
from build_profiles import dump

ROOT = Path(__file__).resolve().parent

def main():
    records = []
    for k in (2,4,8,16,32,1024):
        x = json.loads((ROOT/'artifacts'/f'arity-{k}.json').read_text(encoding='utf-8'))
        layers = []
        for z in x['layers']:
            s,n = z['s'],z['n']
            count = {
                'layer':z['i'],
                'block_commitments_Rq_products':x['main_rank']*s*n,
                'block_commitments_Rq_additions':x['main_rank']*s*(n-1),
                'symmetric_data_Rq_products':3*s*s*n,
                'symmetric_data_inner_product_Rq_additions':3*s*s*(n-1),
                'symmetric_offdiagonal_Rq_additions':3*s*(s-1)//2,
                'symmetric_offdiagonal_half_scalar_products':3*s*(s-1)//2,
                'one_forward_projection_ternary_entries':384*z['N'],
                'three_aggregation_projection_adjoints_ternary_entry_contributions':3*384*z['N'],
                'one_projection_seed_expansion_prefix_hashes':z['seed']['prefix_hashes'],
                'aggregation_power_K_multiplications':z['aggregation_degree'],
                'selected_response_short_challenge_Rq_products':s*n,
                'selected_response_Rq_additions':(s-1)*n,
                'projection_integer_squares':384,
                'selected_response_integer_squares':64*n,
            }
            if not z['terminal']:
                count.update(
                    digit_commitments_Rq_products=x['auxiliary_rank']*(z['bt_columns']+z['bh_columns']),
                    digit_commitments_Rq_additions=x['auxiliary_rank']*(z['bt_columns']+z['bh_columns']-2),
                    decomposed_field_coefficients=64*(x['main_rank']*s+3*s*(s+1)//2),
                    output_digit_coefficients=64*(z['bt_columns']+z['bh_columns']),
                )
            else:
                pivot_columns=16*x['main_rank']
                count.update(pivot_commitment_Rq_products=x['pivot_rank']*pivot_columns,
                             pivot_commitment_Rq_additions=x['pivot_rank']*(pivot_columns-1))
            layers.append(count)
        record = {
            'arity':k,
            'cost_model':'Selected algebraic subroutines, one attempt; no total across unlike units.',
            'excluded_work':'Sparse field applications and sumcheck are unchanged by these parameters. Structured public-operator application is separate from expansion. No machine-instruction or elapsed-time estimate.',
            'carrier':{'streaming_B_evaluations':k+k*(k-1)//2,
                       'streaming_J_conversions':k+k*(k-1)//2,
                       'pole_residue_B_evaluations':k,'pole_residue_J_conversions':k,
                       'multipoint_Q_evaluations_with_cached_sources':k},
            'new_frontend_commitments':{
                'Rq_products':x['front_rank']*(219+12*k+sum(x['front']['auxiliary_chunks'])),
                'Rq_additions':x['front_rank']*(219+12*k+sum(x['front']['auxiliary_chunks'])-2-len(x['front']['auxiliary_chunks'])),
                'separate_incoming_fresh_commitment_Rq_products':k*x['front_rank']*219,
            },
            'field_equality_table':{'K_multiplications':(1<<x['field_rounds'])-1,'K_subtractions':(1<<x['field_rounds'])-1},
            'layers':layers,
            'literal_CRS_bytes':x['crs_bytes'],
            'one_projection_scan_total_ternary_entries':x['projection_trits'],
        }
        records.append(record)
    dump(ROOT/'artifacts/operation_counts.json',records)

if __name__=='__main__':
    main()
