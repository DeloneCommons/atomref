# atomref

atomref is a Python library for curated atomic reference data and transfer
policies for geometry and structure-analysis algorithms.

Copyright (c) 2026 Ivan Chernyshov
License: LGPL-3.0-or-later (see LICENSE and COPYING)

## Third-party material

The initial scaffold reuses and adapts data tables and design ideas from the
Delone Commons `molcryst` repository, also authored by Ivan Chernyshov.

### atomref-proatoms data

`proatomic_density_neutral.zip` is a neutral H–Lr (Z=1–103), 20-bohr-truncated
consumer snapshot derived from:

Ivan Yu. Chernyshov, *atomref-proatoms: spherical atomic and ionic reference
densities*, release 2.0.0, dataset
`pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`.

The released source data and metadata are licensed under Creative Commons
Attribution 4.0 International (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/legalcode

- Concept DOI: 10.5281/zenodo.21291021
- Version DOI for the immutable 2.0.0 archive: 10.5281/zenodo.21291022
- Source repository: https://github.com/DeloneCommons/atomref-proatoms

atomref selected the 103 neutral profiles, retained source rows through the
first grid point above 20 bohr for endpoint bracketing, and repackaged them as a
deterministic single-member ZIP. This data license is separate from atomref's
LGPL-3.0-or-later code license.
