# atomref

The top-level package re-exports the main user-facing API so that most code can
simply do `import atomref as ar`.

::: atomref
    options:
      members:
        - __version__
        - Element
        - canonicalize_element_symbol
        - get_element
        - iter_elements
        - is_valid_element_symbol
        - BuiltinSet
        - CoverageInfo
        - DatasetInfo
        - DatasetRef
        - ElementRadialSet
        - ElementScalarSet
        - QuantityInfo
        - Reference
        - get_builtin_set
        - get_dataset_info
        - get_quantity_info
        - list_dataset_ids
        - list_dataset_infos
        - list_quantities
        - LinearFit
        - LinearTransfer
        - SubstitutionTransfer
        - LookupResult
        - ValuePolicy
        - lookup_value
        - get_value
        - BOHR_TO_ANGSTROM
        - DEFAULT_PROATOMIC_DENSITY_SET
        - PROATOMIC_TAIL_CUTOFF
        - IAS_MINIMUM_RESOLUTION_BOHR
        - IASPositionResult
        - ProatomicDensityProfile
        - ProatomicDensitySet
        - estimate_proatomic_boundary
        - estimate_promolecular_density_minimum
        - estimate_ias_position
        - list_proatomic_density_sets
        - list_proatomic_density_set_infos
        - get_proatomic_density_set
        - get_proatomic_density_set_info
        - get_proatomic_density_profile
        - get_proatomic_density
        - RadiiPolicy
        - RadiiElementAssessment
        - RadiiPolicyAssessment
        - DEFAULT_COVALENT_POLICY
        - DEFAULT_VDW_POLICY
        - list_radii_sets
        - list_radii_set_infos
        - get_radii_set
        - get_radii_set_info
        - lookup_covalent_radius
        - get_covalent_radius
        - lookup_vdw_radius
        - get_vdw_radius
        - assess_radii_policy
        - XHPolicy
        - DEFAULT_XH_POLICY
        - list_xh_sets
        - list_xh_set_infos
        - get_xh_set
        - get_xh_set_info
        - lookup_xh_bond_length
        - get_xh_bond_length
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
