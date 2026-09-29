"""Typed arithmetic counts for the specialized compiler layout."""

def operations(x,c):
    layers=[]
    for z in x['layers']:
        s,n=z['s'],z['n']
        a=dict(layer=z['i'],block_commitment_Rq_products=x['main_rank']*s*n,
            block_commitment_Rq_additions=x['main_rank']*s*(n-1),
            symmetric_Rq_products=3*s*s*n,symmetric_inner_Rq_additions=3*s*s*(n-1),
            symmetric_cross_Rq_additions=3*s*(s-1)//2,
            symmetric_half_scalar_products=3*s*(s-1)//2,
            projection_ternary_contributions=384*z['N'],
            three_projection_adjoints_ternary_contributions=3*384*z['N'],
            seed_prefix_hashes=z['seed']['prefix_hashes'],aggregation_K_multiplications=z['aggregation_degree'],
            short_response_bounded_scalar_ring_products=s*n,short_response_Rq_additions=(s-1)*n,
            projection_integer_squares=384,response_integer_squares=64*n)
        if not z['terminal']:
            a.update(digit_commitment_Rq_products=x['auxiliary_rank']*(z['bt_columns']+z['bh_columns']),
                digit_commitment_Rq_additions=x['auxiliary_rank']*(z['bt_columns']+z['bh_columns']-2),
                digit_input_Fq_coefficients=64*(x['main_rank']*s+3*s*(s+1)//2),digit_output_coefficients=64*(z['bt_columns']+z['bh_columns']))
        else:a.update(pivot_commitment_Rq_products=x['pivot_rank']*16*x['main_rank'],
                      pivot_commitment_Rq_additions=x['pivot_rank']*(16*x['main_rank']-1))
        layers.append(a)
    ell=x['field_rounds'];n=1<<ell;nnz=sum(c['nnz']);k=x['k']
    return dict(cost_model='Separate algebraic units; counts for specified routines, not elapsed time',
        canonical_encoding=dict(value_bit_outputs=48*c['free_coefficients'],
            helper_bit_outputs=(12 if c['special'] else 48)*c['free_coefficients'],
            constant_coordinate_outputs=1,physical_scatter_assignments=c['columns']-1,
            fixed_physical_nonzero_coordinates=c['fixed_energy'],
            scalar_arithmetic_note='Comparator generation uses integer bit extraction and products; not charged as K operations'),
        sparse_R1CS=dict(nnz_A_B_C=c['nnz'],generic_apply_K_multiplications=nnz,generic_apply_K_additions=nnz,
            generic_transpose_K_multiplications=nnz,generic_transpose_K_additions=nnz,
            scope='Each nonzero coefficient times one input, accumulated from zero; ±1 specialization may reduce products'),
        field=dict(padded_rows=n,equality_table_K_multiplications=n-1,equality_table_K_subtractions=n-1,
            dense_three_table_fold_K_multiplications=3*(n-1),dense_three_table_fold_K_additions=3*(n-1),
            dense_three_table_fold_K_subtractions=3*(n-1),
            standard_sumcheck_pair_products_K_multiplications=3*(n-1),standard_sumcheck_pair_products_K_subtractions=6*(n-1),
            suffix_weighted_pair_accumulation_K_multiplications=3*(n-1),suffix_weighted_pair_accumulation_K_additions=3*(n-1),
            scope='Dense algebraic reference loops, not the sparse/dictionary shortcuts used by the transcript test; per-round interpolation, suffix-table construction and scalar message operations are separate'),
        new_frontend_commitments=dict(Rq_products=x['front_rank']*(219+12*k+c['auxiliary_columns']),
            Rq_additions=x['front_rank']*(219+12*k+c['auxiliary_columns']-3)),
        fresh_commitments_separate=dict(Rq_products=k*x['front_rank']*219),
        public_affine_offset=dict(nonzero_physical_coefficients=c['fixed_energy'],
            offset_commitment_scalar_contributions=4*64*c['fixed_energy'],
            scope='Direct coefficient-column accumulation; offset depends on CRS and fixed format and may be precomputed',
            ring_multiplications=0),
        carrier=dict(streaming_B_evaluations=k+k*(k-1)//2,pole_residue_B_evaluations=k,
            pole_residue_J_conversions=k,multipoint_Q_evaluations_with_cached_sources=k),
        backend_layers=layers,projection_terms_all_layers=x['projection_trits'],literal_CRS_bytes=x['crs_bytes'],
        exclusions='No total across operation units; no wall-clock results; field and commitment routines are specified separately')
