# atomref.radii

This is the main user-facing module for radii workflows.

It provides radii policies, packaged radii-set discovery, lookup helpers, and
policy-assessment reports.

::: atomref.radii
    options:
      members:
        - RadiiKind
        - RadiiSet
        - RadiiPolicy
        - RadiiElementAssessment
        - RadiiPolicyAssessment
        - DEFAULT_COVALENT_POLICY
        - DEFAULT_VDW_POLICY
        - list_radii_sets
        - list_radii_set_infos
        - get_radii_set_info
        - get_radii_set
        - lookup_covalent_radius
        - get_covalent_radius
        - lookup_vdw_radius
        - get_vdw_radius
        - assess_radii_policy
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
