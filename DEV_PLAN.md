# atomref 0.2.x development plan

> **Status:** fourth review draft — Stage 4 replanned after numerical review  
> **Plan lifecycle state:** `ACTIVE`  
> **Primary target:** `atomref 0.2.0` — dataset architecture, neutral proatomic density, two-mode pairwise boundary/IAS-proxy analysis, and executed notebooks  
> **Planned follow-up:** `atomref 0.2.1` — notebook/documentation infrastructure, complete API reference, and README positioning  
> **Source data:** `atomref-proatoms 2.0.0`, dataset `pbe0_sfx2c_dyallv4z_h-lr_spherical_v2`

## 1. Purpose and lifecycle of this file

This root-level `DEV_PLAN.md` is the authoritative implementation plan for the
`0.2.x` development cycle. It is written for a coding agent working in the
repository, but it should remain understandable to a human reviewer.

The plan has three scopes:

1. **`0.2.0` binding implementation work** — generic packaged-dataset loading,
   neutral radial density data, interpolation, two-mode pairwise
   boundary/IAS-proxy analysis, tests, and executed explanatory notebooks.
2. **`0.2.1` planned documentation work** — direct rendering of saved executed
   notebooks, richer notebook explanations, complete docstring-based API
   reference, and a marketing-oriented README rewrite.
3. **Future reference only** — ions, additional properties, vectorized
   evaluation, and three-dimensional grid-density generation. These items are
   recorded to protect future compatibility but MUST NOT be implemented during
   `0.2.0` or `0.2.1` unless the repository owner explicitly changes the scope.

Use this file to:

- understand the scientific and product contract before changing code;
- implement the work in the stated order;
- record completed stages and justified deviations;
- avoid adding abstractions, files, or process machinery that the project does
  not need;
- preserve a clear distinction between current work and future ideas;
- verify that each release is complete.

Do **not** copy this whole file into the public documentation. During `0.2.1`,
move only durable user-facing or architectural information into the existing
documentation. The complete execution plan should remain at the repository root
until the planned cycle is finished.

The current duplicate page at `docs/dev/dev_plan.md` should be removed in
`0.2.1`, together with its MkDocs navigation entry. There should ultimately be
only one development plan.

After `0.2.1` is released, this file may be:

- replaced by the next small roadmap;
- shortened to unresolved future work;
- or removed after the changelog and release history preserve completed work.

### 1.1 Plan authority, terminal states, and external review

This file is the central control document for LLM-driven implementation of the
work described here. The implementation agent may update checkboxes, stage
results, deviations, and closeout records, but it MUST NOT silently extend the
scope or turn future-reference items into active work.

The plan has four lifecycle states:

```text
ACTIVE
COMPLETE_AWAITING_REVIEW
REPLAN_REQUIRED
CLOSED
```

Their meanings are:

- **`ACTIVE`** — the accepted plan authorizes implementation of the current
  stage.
- **`COMPLETE_AWAITING_REVIEW`** — the implementation agent believes every
  binding requirement and acceptance criterion has been completed. It has
  filled the closeout record and stopped further feature development pending an
  independent review.
- **`REPLAN_REQUIRED`** — implementation cannot safely continue under the
  current plan because of an unexpected scientific, architectural, data,
  licensing, tooling, or repository constraint. The agent has documented the
  blocker and stopped rather than inventing a replacement plan.
- **`CLOSED`** — an external reviewer has checked the implementation or the
  blocker report and formally closed this plan as completed, superseded, or
  abandoned.

An **external reviewer** means the repository owner, another human reviewer, or
a separate planning/review agent that is not simply the implementation agent
continuing its own task without an independent review step.

When all planned work appears complete, the implementation agent MUST:

1. run every applicable release and acceptance check;
2. complete the closeout record in Section 20;
3. change the lifecycle state to `COMPLETE_AWAITING_REVIEW`;
4. state exactly what was implemented, tested, deferred, or intentionally
   omitted;
5. stop adding functionality until an external reviewer approves or requests
   corrections.

When the plan becomes unexecutable, the implementation agent MUST:

1. stop at the smallest safe repository state;
2. preserve or clearly identify all partial changes;
3. record what happened, why it blocks the plan, evidence gathered, approaches
   attempted, and which decisions require replanning;
4. state whether the partial branch should be retained, reverted, or used as a
   basis for a new plan;
5. change the lifecycle state to `REPLAN_REQUIRED`;
6. stop implementation until an external reviewer accepts a revised plan.

After the state is `COMPLETE_AWAITING_REVIEW`, `REPLAN_REQUIRED`, or `CLOSED`,
an implementation agent asked to “continue development” MUST explain that the
current plan no longer authorizes additional coding. A new or revised plan must
be prepared and externally reviewed first. The agent MAY help draft that plan in
a separate planning task when asked, but MUST NOT resume implementation until
the new plan is accepted and marked `ACTIVE`.

## 2. Normative language and implementation freedom

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** express
the intended strength of a requirement.

This plan separates decisions into three classes.

### 2.1 Binding contract

A binding contract defines scientific meaning, public behavior, provenance,
units, supported range, compatibility, or release acceptance. It MUST be
preserved unless the repository owner explicitly changes the plan.

Examples:

- neutral H–Lr coverage;
- the 20-bohr public radius limit;
- no density correlation or element substitution;
- no runtime dependency on `atomref-proatoms`;
- reproducible source verification;
- explicit units and failures outside the supported domain;
- keeping the stable proatomic-boundary mode distinct from the optional
  promolecular-minimum mode, with the cutoff and practical resolution explicit.

### 2.2 Preferred first design

A preferred design is the expected starting point for implementation. The agent
MAY replace it with a materially clearer, smaller, safer, or faster design when
all binding behavior and tests remain intact.

Any deviation MUST be reported with:

1. the original proposed design;
2. the observed problem;
3. the replacement;
4. why the replacement is better;
5. which tests protect the same contract.

Examples:

- exact class and function names;
- whether two closely related result classes are combined;
- precise internal CSV column names;
- exact practical valley-refinement implementation;
- whether density and IAS implementation share one module or use two modules.

### 2.3 Open decision

An open decision is intentionally left for focused design work during the
relevant stage. It MUST be resolved explicitly before implementation of the
dependent behavior.

The earlier open decision about exhaustive IAS local-minimum enumeration is
resolved by Sections 10 and 11. `0.2.0` uses two explicit modes: a stable
proatomic-boundary mode and a resolution-limited promolecular-minimum mode.
Final public spelling may still be adjusted during Stage 4B, but the scientific
meaning, cutoff policy, default mode, and invariants are binding.

## 3. Agent operating rules

### 3.1 Keep the repository small

Before adding any new file, abstraction, schema, public class, or tool, ask:

> Considering the probable maximum future scope—ionic variants of some
> properties, a small number of additional atomic properties, and optional
> spatial sampling of radial densities—does the project genuinely need this
> object or file?

Prefer:

- one generic packaged-dataset dispatcher over separate unrelated loaders;
- the existing registry over a second metadata registry;
- one feature module over several one-purpose internal modules;
- one maintained notebook execution/checking tool over parallel exporters and
  validators;
- direct notebook rendering over generated duplicate Markdown copies;
- existing release and validation tools extended in place;
- straightforward dataclasses, protocols, unions, and functions over a
  framework.

Do not add:

- `AGENTS.md`;
- architecture-decision-record directories;
- a second development-plan copy;
- a plugin system;
- a general multidimensional scientific-data framework;
- a generic atomic-state selection engine;
- a new runtime dependency merely to simplify a small numerical routine;
- separate documentation pages when one existing page or one combined new page
  is clearer;
- generated copies of notebooks when MkDocs can render the actual notebook.

A maintainer-only script in `tools/` is justified when it makes a committed
scientific artifact reproducible or verifiable. Such a tool is not a user-facing
package feature and MUST NOT be presented as one.

### 3.2 Protect the working scalar policy core

The existing scalar registry metadata, policy, transfer, radii, and X–H behavior
is working and well tested.

The implementation MUST NOT:

- apply `ValuePolicy` to radial values;
- apply `SubstitutionTransfer` or `LinearTransfer` to radial profiles;
- change existing default radii or X–H results;
- break public `0.1.x` APIs;
- perform speculative cleanup outside the affected code.

However, the packaged-dataset loader itself MUST be generalized so that
`get_builtin_set()` and the dataset-centered discovery machinery work for both
scalar and radial packaged sets. This is a focused architecture change required
by the new feature, not an unrelated policy rewrite.

Policy code may receive small type-narrowing or helper changes so that it
explicitly requests scalar datasets from the now-generic loader. Its scientific
behavior must remain unchanged.

### 3.3 Preserve project conventions

- Runtime code remains pure Python with no required third-party dependencies.
- Optional notebook/documentation dependencies do not become runtime
  dependencies.
- Runtime access performs no network requests.
- `README.md` remains generated from `docs/index.md`; do not edit the generated
  README as the source of truth.
- Generated profile data MUST NOT be hand-edited.
- Public objects remain typed and compatible with the shipped `py.typed`.
- Package data MUST be validated in both wheel and source distribution.
- Existing commands and CI checks remain operational until deliberately
  replaced by a smaller equivalent in `0.2.1`.
- New public names MUST be added deliberately to `atomref.__all__` and the
  public-API test.
- New behavior MUST have tests before the stage is considered complete.
- Notebooks committed as release examples MUST contain saved execution counts
  and outputs.

### 3.4 Work stage by stage

Complete, test, and report each stage before proceeding.

At the end of each stage, provide:

- a concise change summary;
- files added, removed, or substantially changed;
- commands run and their results;
- any deviation from this plan;
- unresolved questions;
- the suggested conventional commit message;
- the next stage.

Do not combine unrelated stages into one unreviewable change.

Do not begin the `0.2.1` documentation overhaul until the repository owner has
accepted the `0.2.0` functionality and release state.

## 4. Product goal

`atomref 0.2.0` should establish the package as a small source of **reference
atoms for structure algorithms**, not only a radii lookup package.

The release should support these workflows:

```python
import atomref as ar

rho = ar.get_proatomic_density("O", 0.75)

boundary = ar.estimate_proatomic_boundary("C", "O", 1.43)
minimum = ar.estimate_promolecular_density_minimum("C", "O", 1.43)

# One convenience entry point with an explicit policy choice.
selected = ar.estimate_ias_position("C", "O", 1.43, mode="boundary")
```

The density call evaluates a frozen neutral spherical proatomic density.

The pairwise helpers expose two related but scientifically different
approximations:

- **`boundary` mode** returns a stable neutral-proatom divider. It uses exact
  homonuclear symmetry, equal proatomic contributions in the meaningful-overlap
  region, and the midpoint between fixed low-density contours when the contours
  no longer overlap.
- **`minimum` mode** searches for one practically resolved minimum of the summed
  promolecular line density inside the meaningful-overlap region. This is the
  more Bader-oriented proxy, but it is optional, resolution-limited, and may
  report ambiguity or no resolved minimum.

The release is successful when a quantum-chemistry, crystallographic, or
molecular-software developer can immediately understand:

- what the supplied profiles represent and where they came from;
- how to evaluate them;
- the difference between the two pairwise modes;
- why `boundary` is the default;
- where the fixed tail cutoff enters;
- what numerical domain is supported;
- what each result does and does not claim physically.

## 5. Release scope

### 5.1 `0.2.0` included work

`0.2.0` includes:

- a generic `get_builtin_set()` dispatcher that loads every packaged dataset
  through the same dataset-centered machinery;
- one packaged neutral H–Lr spherical proatomic-density dataset;
- reproducible construction from the immutable `atomref-proatoms 2.0.0`
  release;
- profile access by element symbol or atomic number through existing element
  normalization;
- scalar radial-density evaluation;
- independent radius-coordinate and density-output unit selection;
- a strict public radius domain of `0 <= r <= 20 bohr`;
- positive-region log–log interpolation;
- a cached fixed neutral-proatom tail radius for every packaged element at
  `1e-4 electron/bohr^3`;
- a stable pairwise proatomic-boundary estimator;
- an optional, cutoff-bounded and resolution-limited promolecular-density
  minimum estimator;
- a convenience dispatcher with an explicit `mode` and default
  `mode="boundary"`;
- exact homonuclear midpoint behavior in both modes;
- explicit low-density-gap, one-atom-dominance, boundary-dominated,
  no-resolved-minimum, and competing-minimum diagnostics;
- pair-reversal and unit-invariance guarantees;
- explicit provenance, method, cutoff, units, limitations, and data licensing;
- an executed supporting notebook explaining the Stage 4 method decision;
- one executed feature notebook for proatomic density and pairwise workflows,
  including explanatory Markdown cells and plots;
- minimum accurate user/API documentation needed to release the functionality;
- tests, packaging checks, and release metadata.

### 5.2 `0.2.1` planned work

`0.2.1` is a documentation and discoverability release. It includes:

- replacing transient notebook execution with reproducible execution that saves
  and verifies notebook outputs;
- executing and saving all shipped notebooks;
- adding short explanatory Markdown before each logical code section;
- directly rendering `.ipynb` files in MkDocs, including plots and rich output;
- removing generated notebook Markdown copies and their exporter when direct
  rendering is accepted;
- configuring `mkdocstrings` to show complete typed signatures and structured
  Parameters, Returns, Raises, Attributes, and Examples sections;
- upgrading all public docstrings to a consistent structured style;
- reviewing API-page member selection so every intended public type and
  parameter is documented;
- substantially improving the README/home page as a product introduction;
- removing the duplicate documentation copy of the development plan;
- simplifying notebook/documentation CI after the new workflow is stable.

`0.2.1` MUST NOT change density, cutoff radii, pairwise mode semantics, or
selected coordinates except to fix a confirmed defect with an explicit
changelog entry and regression test.

### 5.3 Excluded from `0.2.0` and `0.2.1`

These releases do not include:

- ionic profile selection;
- fractional-charge interpolation;
- atom typing or environment-dependent profiles;
- correlations between profile datasets;
- element substitution for missing profiles;
- reconstruction of one basis-set profile from another;
- user-defined radial profile datasets;
- vectorized NumPy density APIs;
- three-dimensional density-grid generation;
- periodic image summation;
- arbitrary interpolation modes;
- far-tail extrapolation;
- profile evaluation beyond 20 bohr;
- molecular electron densities;
- exact QTAIM or other rigorous molecular-density boundaries;
- an automatic Hirshfeld or Hirshfeld-I cycle;
- a generalized arbitrary-rank data registry;
- new required runtime dependencies.

### 5.4 Versions

The primary feature release is **`0.2.0`**, not `0.1.5`.

It adds:

- a new scientific data family;
- a new radial payload shape;
- generalized packaged-dataset dispatch;
- new numerical semantics;
- new public APIs;
- a derived pairwise analysis.

The documentation and discoverability work is **`0.2.1`** because it follows
and documents a stabilized `0.2.0` API rather than forcing the scientific
implementation and the complete presentation overhaul into one review.

A later grid-density or ion/state release should receive its own version after
separate design review. Do not assign that version in advance.

## 6. Scientific data contract

### 6.1 Upstream source

The packaged profiles MUST be derived from:

```text
project:
  atomref-proatoms

release:
  2.0.0

version-specific DOI:
  10.5281/zenodo.21291022

concept DOI:
  10.5281/zenodo.21291021

upstream dataset_id:
  pbe0_sfx2c_dyallv4z_h-lr_spherical_v2
```

Pinned source files:

```text
profiles.csv
sha256:
  b5520ab009542d52098dd6dbb920966d8d13377a4a5004f584a7bd15cd41c299

metadata.json
sha256:
  32c833ca69fa0f7eb9ed32841aafc638123ff872861e636156610e417fc4c514

basis_id:
  dyall-v4z

basis_sha256:
  0ee543855f8b1e7fbe9868d4abb844d8e8cc8b8c2694067b2b40de014bb4be94
```

The snapshot builder MUST reject a source whose pinned hashes, dataset identity, data
version, basis identity, or basis checksum do not match.

### 6.2 Scientific identity

The consumer metadata MUST preserve at least:

```text
profile data version:
  2.0.0

electronic method:
  PBE0

SCF model:
  self-consistent spherical fractional-occupation UKS

relativity:
  spin-free one-electron X2C

basis:
  dyall-v4z

native radius unit:
  bohr

native density unit:
  electron / bohr^3

charge scope:
  neutral atoms only

element coverage:
  H through Lr, Z = 1..103
```

The public documentation MUST explain that these are method-, basis-, state-,
and sphericalization-defined reference densities. They are not unique
basis-independent atomic observables.

### 6.3 Neutral-state selection

The snapshot builder MUST use upstream metadata, not column-name guessing alone, to
select profiles.

Required selection:

```text
charge == 0
exactly one selected state for every Z from 1 through 103
```

The snapshot builder MUST fail when:

- an element is missing;
- more than one neutral state is selected for an element;
- a selected column is missing from the CSV;
- the selected metadata and column metadata disagree.

The consumer data does not need to duplicate configuration, multiplicity,
occupation policy, state labels, SCF artifact paths, or the full upstream
metadata.

The package metadata should state that detailed state and generation metadata
remain available in the exact `atomref-proatoms 2.0.0` archive.

### 6.4 Radius truncation and bracketing

The public validity domain is:

```text
0 <= r <= 20 bohr
```

The upstream logarithmic grid does not contain exactly 20 bohr. The snapshot
SHOULD retain source rows through the first source point above 20 bohr so the
public endpoint remains bracketed by original data.

For the pinned source, the expected facts are:

```text
last source point below 20 bohr:
  19.865456344881434 bohr

first source point above 20 bohr:
  20.1644204667093 bohr

number of retained rows including the bracketing point:
  1127
```

The point above 20 bohr is an internal interpolation bracket. It does not expand
the public validity domain.

The snapshot validation MUST verify that all selected densities are finite and
strictly positive throughout the retained range. Thus the consumer package
never encounters the upstream far-tail zeros during valid use.

### 6.5 Why the public limit is 20 bohr

The 20-bohr boundary is a product decision, not a statement that the upstream
60-bohr data are invalid.

The intended use is empirical or semi-empirical structure analysis, often on
experimental structures. At very remote distances:

- absolute densities are extremely small;
- tail behavior is increasingly sensitive to computational details;
- small structural or numerical changes can dominate the value;
- the data no longer add useful information for the intended IAS helper.

The limit also provides a simple numerical contract:

- no tail extrapolation;
- no numerical underflow zeros in the packaged domain;
- no silent zero-fill behavior;
- no ambiguity about whether an out-of-range value is physical or artificial.

### 6.6 Packaged representation

The consumer representation is one deterministic single-member ZIP archive in
the existing package data directory:

```text
src/atomref/data/proatomic_density_neutral.zip
```

The archive MUST contain exactly one regular file named:

```text
proatomic_density_neutral.csv
```

It remains a container for a plain wide CSV, not a binary scientific-data
format.

Preferred logical structure:

```text
r_bohr,z001,z002,...,z103
```

or another equally simple deterministic Z-keyed header.

Binding requirements:

- one shared radius column;
- one density column per Z from 1 through 103;
- columns ordered by increasing Z;
- exact source decimal values retained where practical;
- deterministic CSV bytes, row ordering, column ordering, and LF line endings;
- exactly one archive member named `proatomic_density_neutral.csv`;
- no directory entries or additional archive members;
- fixed member timestamp `(1980, 1, 1, 0, 0, 0)`;
- normalized Unix platform metadata (`create_system = 3`) and regular-file
  mode metadata (`external_attr = 0o100644 << 16`, `internal_attr = 0`);
- empty archive and member comments;
- no uncontrolled ZIP extra fields;
- fixed `ZIP_DEFLATED` compression with explicit compression level 9;
- no duplicated symbol columns;
- no ionic or configuration data;
- no second large metadata file.

The element symbol mapping MUST come from the existing element registry.

All interpretive metadata SHOULD live in the existing `registry.json`, with
license/citation text also added to `NOTICE.md` and public documentation.

This owner-approved ZIP representation is binding for the `0.2.x` consumer
snapshot. Do not substitute another container or introduce a binary scientific
data format.

### 6.7 Licensing and attribution

The `atomref` code remains under its existing LGPL licensing.

The imported `atomref-proatoms` data are CC BY 4.0. The release MUST:

- identify the data license in registry metadata;
- update `NOTICE.md`;
- cite the concept and version-specific DOI;
- name the exact upstream dataset;
- state that the data are a neutral, truncated consumer snapshot;
- ensure the attribution is present in built distributions through packaged
  metadata and/or configured license/notice files;
- test that the required attribution metadata is shipped.

Do not silently present the data as covered only by the code license.

## 7. Registry and architecture contract

### 7.1 All packaged datasets use the same machinery

Every packaged dataset MUST participate in the existing dataset-centered
operations:

```python
list_quantities()
get_quantity_info(...)
list_dataset_ids(...)
list_dataset_infos(...)
get_dataset_info(...)
get_builtin_set(...)
```

`get_builtin_set(DatasetRef(...))` MUST load both existing scalar datasets and
the new radial dataset.

A separate public loader that bypasses `get_builtin_set()` is not an acceptable
final architecture for `0.2.0`.

The current scalar-only implementation is not a fundamental blocker. It
currently assumes:

```text
element-domain + dense-by-Z CSV + one scalar column
```

The focused refactor should instead dispatch from explicit storage metadata.

Preferred registry storage identifiers:

```text
element_scalar_csv
element_radial_csv_zip
```

or an equivalent pair of clear stable identifiers.

The registry remains the single source of truth for:

- quantity and set identity;
- aliases;
- coverage;
- scientific metadata;
- storage kind, filename, and archive member where applicable;
- provenance and references;
- loading dispatch.

### 7.2 Preferred loaded-set model

Preferred public/internal types:

```python
ElementScalarSet
ElementRadialSet
BuiltinSet = ElementScalarSet | ElementRadialSet
```

`ElementRadialSet` may be named `ProatomicDensitySet` if a truly generic radial
type would add abstraction without present value. The important contract is
that the object returned by `get_builtin_set()` is the actual loaded packaged
set and carries:

- `ref`;
- `info`;
- element coverage;
- access to an immutable profile by symbol/Z;
- shared grid and profile data;
- no policy behavior.

The exact union/type-alias placement is a preferred design.

### 7.3 Scalar policy type narrowing

The scalar policy core must continue to accept scalar datasets only.

The current internal names:

```python
DatasetLike
resolve_dataset_like(...)
```

are scalar in behavior despite generic names. During the focused refactor,
prefer clearer names such as:

```python
ScalarDatasetLike
resolve_scalar_dataset_like(...)
```

These are internal and can be renamed without public breakage.

Alternative: retain the old internal name but add an explicit type guard that
raises a clear `DatasetError` when a radial set is supplied. The clearer rename
is preferred.

`get_radii_set()` and `get_xh_set()` should continue to return
`ElementScalarSet` and must validate/narrow the generic `get_builtin_set()`
result.

The policy engine, transfer fitting, fallback, and placeholder behavior must not
be generalized to functions.

### 7.4 Failure contingency

If implementation reveals a genuine blocker to generic `get_builtin_set()`
dispatch:

1. stop before adding a bypass as permanent architecture;
2. document the concrete blocker and affected call graph;
3. implement the smallest reviewed temporary adapter only with owner approval;
4. add a named follow-up item to `0.2.1` or the next patch;
5. protect the temporary behavior with tests;
6. do not claim that dataset machinery is unified until it actually is.

The expected outcome is still to complete the generic dispatcher in `0.2.0`.

### 7.5 Minimal implementation structure

Preferred new files for `0.2.0`:

```text
src/atomref/proatoms.py
src/atomref/data/proatomic_density_neutral.zip
tools/build_proatomic_density_snapshot.py
tests/proatoms/test_dataset.py
tests/proatoms/test_density.py
tests/proatoms/test_ias.py
notebooks/04-ias-method-selection-study.ipynb
notebooks/05-proatomic-density-and-ias.ipynb
docs/dev/ias_method_selection.md
```

The exact test split is flexible.

The generic radial set and storage dispatch may live in `registry.py`; density
evaluation and IAS analysis should initially live in `proatoms.py`.

Do not add a separate:

- `_density_data.py`;
- `ias.py`;
- profile-manifest JSON;
- schema directory;
- numerical-contract document;
- data-specific documentation directory;

unless actual implementation evidence shows that the combined design is
unmanageable.

### 7.6 Existing metadata classes

`CoverageInfo` should be generalized in wording from “element-indexed scalar
dataset” to “element-indexed dataset.” Its fields are sufficient for H–Lr
coverage.

`DatasetInfo.storage` is already a generic metadata mapping and should carry:

- storage kind;
- filename;
- archive member name where applicable;
- radius column;
- density-column convention;
- native coordinate unit;
- native density unit;
- public maximum radius;
- retained bracketing radius;
- interpolation contract identifier;
- source project, release, dataset ID, hashes, and license.

Avoid adding fields to public metadata dataclasses unless the information cannot
be represented clearly in the existing structure.

### 7.7 Caching

`get_builtin_set()` is currently cached by `DatasetRef`. Preserve equivalent
caching for radial sets.

The generic dispatcher may delegate to format-specific cached loaders, but
repeated calls for the same canonical dataset should return the same immutable
loaded-set object or equivalent shared cached data.

## 8. Density API contract

### 8.1 Public concept

The API should use “proatomic density,” not the ambiguous abbreviation `ED`.

Preferred public names:

```python
DEFAULT_PROATOMIC_DENSITY_SET
ProatomicDensitySet
ProatomicDensityProfile

list_proatomic_density_sets()
list_proatomic_density_set_infos()
get_proatomic_density_set()
get_proatomic_density_set_info()
get_proatomic_density_profile()
get_proatomic_density()
```

This list is a preferred first design. It MAY be reduced when an existing generic
registry helper already provides the same operation clearly.

At minimum, the release MUST provide:

```python
get_proatomic_density_profile(...)
get_proatomic_density(...)
```

and a clear way to inspect the exact dataset metadata.

### 8.2 Preferred usage

```python
import atomref as ar

rho_o = ar.get_proatomic_density(
    "O",
    0.75,
    radius_unit="angstrom",
    density_unit="electron/bohr^3",
)

profile = ar.get_proatomic_density_profile("O")
rho_o_bohr = profile(
    1.5,
    radius_unit="bohr",
    density_unit="electron/bohr^3",
)
```

The profile object SHOULD be callable or expose one obvious evaluation method.

### 8.3 Element handling

The API MUST follow existing element behavior:

- ordinary symbols are canonicalized;
- `D` and `T` use the hydrogen electronic profile;
- invalid symbols return `None`;
- elements beyond Lr return `None`;
- no neighboring-element or correlated fallback occurs.

The canonical dataset map is keyed internally by atomic number.

### 8.4 Scalar scope

The initial public API evaluates one scalar radius at a time.

It MUST NOT require NumPy and SHOULD NOT accept arbitrary iterables in `0.2.0`.

Repeated evaluation should be supported efficiently through the cached profile
object.

A future vectorized API may be added separately if real downstream profiling
shows it is useful.

### 8.5 Units

Radius coordinates and density values use independent unit parameters.

Canonical radius units:

```text
angstrom
bohr
```

Canonical density units:

```text
electron/bohr^3
electron/angstrom^3
```

Preferred defaults:

```text
radius_unit = "angstrom"
density_unit = "electron/bohr^3"
```

This reflects common structural input conventions while preserving the familiar
atomic-density scale used for values such as approximately `0.003` or `0.001`
electron/bohr³.

Preferred density call:

```python
rho = get_proatomic_density(
    "O",
    0.75,
    radius_unit="angstrom",
    density_unit="electron/bohr^3",
)
```

The profile object should use the same independent arguments.

Short aliases such as `e/bohr^3` MAY be accepted, but documentation and result
metadata should emit one canonical form.

The implementation MUST use named, tested conversion constants. Do not scatter
conversion literals through the code.

Changing `density_unit` must change only reported density values. It must not
change:

- selected interpolation interval;
- cutoff radii or contour-overlap geometry;
- selected pairwise mode or method;
- returned coordinate;
- resolved-minimum identity;
- ambiguity, domination, or low-density-gap status.

### 8.6 Error and missing-data behavior

Binding behavior:

| Situation | Result |
|---|---|
| Invalid or unsupported element | `None` |
| Missing packaged dataset | `DatasetError` |
| Unknown radius or density unit | `ValueError` |
| Negative radius | `ValueError` |
| Non-finite radius | `ValueError` |
| Radius above 20 bohr after unit conversion | `ValueError` |
| Valid radius and supported element | finite positive `float` |

This follows the package distinction between:

- absent scientific data: return `None`;
- malformed or out-of-contract request: raise.

### 8.7 Lazy loading and caching

The compressed data MUST load lazily.

Repeated profile retrieval or evaluation MUST NOT repeatedly parse the file.

The implementation SHOULD cache:

- the loaded shared radius grid;
- the Z-indexed profile table or immutable profile views;
- dataset metadata resolution.

The public API MUST not expose mutable references to cached shared data.

## 9. Interpolation contract

### 9.1 Supported numerical region

The packaged retained interval contains strictly positive density values for all
103 profiles.

Therefore, valid public interpolation does not need a zero-density branch.

If a future imported snapshot contains a nonpositive value within the retained
bracketing region, import or load validation MUST fail rather than silently
changing interpolation behavior.

### 9.2 Contract identifier

Registry metadata and result provenance SHOULD use a stable identifier such as:

```text
loglog_positive_bracketed_v1
```

The exact string may change before implementation, but it must be stable within
the release and documented.

### 9.3 Evaluation rules

For one profile with source knots `(r_i, rho_i)`:

1. Reject non-finite and negative query radii.
2. For `0 <= r <= r_min`, return `rho(r_min)`.
3. At an exact stored radius, return the exact stored density.
4. Between two positive neighboring knots, interpolate linearly in
   `log(r)` and `log(rho)`.
5. Allow evaluation at exactly 20 bohr using the retained bracketing point.
6. Reject values above 20 bohr.
7. Perform no tail extrapolation and no zero fill.
8. Return a finite positive scalar in the selected output units.

The origin rule is a finite-grid convention. Documentation must not describe it
as an exact nuclear-density evaluation.

### 9.4 Implementation preference

Use only the standard library, for example:

- `bisect` for interval location;
- `math.log` and `math.exp`;
- immutable tuples or similarly simple storage.

The implementation SHOULD avoid rebuilding logarithm arrays on every call.
Precomputed log-radius and, if useful, log-density values may be cached.

### 9.5 Relationship to the upstream interpolation issue

An issue should be opened in `atomref-proatoms` to replace its global
linear-fallback behavior with interval-local handling for profiles that contain
far-tail zeros.

`atomref 0.2.0` does not need to wait for an upstream release because:

- it imports pinned v2.0.0 values;
- it restricts its domain to 20 bohr;
- all retained values are strictly positive;
- it implements its own small dependency-free consumer interpolation.

The two projects should still document compatible positive-positive log–log
behavior.

## 10. Pairwise proatomic boundary and IAS-proxy scientific contract

### 10.1 Two related quantities, not one hidden policy

For atoms A and B separated by distance `R`, define `x` from A toward B:

```text
A ---- x ----> B
0             R
```

The component and summed neutral-promolecular line densities are:

\[
\rho_A(x),\qquad \rho_B(R-x),\qquad
f(x;R)=\rho_A(x)+\rho_B(R-x)
\]

for `0 <= x <= R`.

`0.2.0` deliberately exposes two different pairwise estimates:

1. **Proatomic boundary** — a stable geometric divider based on equal neutral
   proatomic contributions, with a fixed low-density contour fallback.
2. **Promolecular density minimum** — one practically resolved minimum of
   `f(x;R)` inside a region where both proatomic contributions remain above the
   fixed tail cutoff.

They MUST NOT be presented as interchangeable definitions. The first is the
production default because it is unique, fast, and stable. The second is
available because a line-density minimum is closer in spirit to a
bond-critical-point coordinate and is useful for Bader-oriented calibration,
but it is a neutral-promolecular proxy rather than a molecular QTAIM result.

### 10.2 Interpretation and naming

Neither mode returns:

- a QTAIM zero-flux surface;
- a molecular-density topological critical point;
- an environment-relaxed atomic boundary;
- an ionic, charged, or self-consistent stockholder boundary;
- proof of a bond or interaction.

User-facing documentation SHOULD use:

- “neutral-proatom boundary estimate” for `boundary` mode;
- “promolecular line-density minimum” or “promolecular IAS proxy” for
  `minimum` mode;
- “pairwise IAS-position proxy” only for the mode-selecting convenience API.

The phrase “most probable position” MUST NOT be used because no probability
model is defined.

Scientific reference context:

- molecular QTAIM basin boundaries are zero-flux surfaces of the molecular
  density: R. F. W. Bader, *Chemical Reviews* **91** (1991), 893–928,
  `doi:10.1021/cr00005a013`;
- the equal-proatom rule is a pairwise stockholder balance based on free-atom
  reference densities: F. L. Hirshfeld, *Theoretica Chimica Acta* **44**
  (1977), 129–138, `doi:10.1007/BF00549096`.

These references motivate the interpretation; they do not turn either neutral-
proatom mode into a molecular QTAIM calculation.

### 10.3 Public functions and default policy

Preferred public API:

```python
estimate_proatomic_boundary(
    atom_a,
    atom_b,
    distance,
    *,
    distance_unit="angstrom",
    density_unit="electron/bohr^3",
    set_id=DEFAULT_PROATOMIC_DENSITY_SET,
)

estimate_promolecular_density_minimum(
    atom_a,
    atom_b,
    distance,
    *,
    distance_unit="angstrom",
    density_unit="electron/bohr^3",
    set_id=DEFAULT_PROATOMIC_DENSITY_SET,
)

estimate_ias_position(
    atom_a,
    atom_b,
    distance,
    *,
    mode="boundary",
    distance_unit="angstrom",
    density_unit="electron/bohr^3",
    set_id=DEFAULT_PROATOMIC_DENSITY_SET,
)
```

Binding behavior:

- `mode` accepts only `"boundary"` and `"minimum"` in `0.2.0`;
- the default is `"boundary"`;
- the dispatcher calls the same internal implementation as the corresponding
  direct function;
- `minimum` mode MUST NOT silently fall back to `boundary` mode;
- callers can compare the two direct results without hidden policy changes.

The exact public names remain a preferred first design. Any rename MUST preserve
these three roles and the explicit default.

### 10.4 Input domain and units

Binding input rules:

- both elements must have profiles;
- distance must be finite and strictly positive;
- distance must not exceed 20 bohr after conversion;
- the result coordinate is measured from atom A toward atom B;
- all reported positions use `distance_unit`;
- component and summed densities use `density_unit`;
- D/T follow hydrogen behavior;
- missing element profiles return `None`;
- invalid distance, mode, or unit raises `ValueError`.

All scientific decisions MUST be performed in bohr and electron/bohr³. Output
conversion occurs only after method selection, status classification, and
coordinate calculation. Changing `density_unit` MUST NOT change geometry,
method, status, or ambiguity.

No universal lower distance such as `0.5 angstrom` is imposed. Extremely short
or dominated pairs are handled by explicit statuses instead of an arbitrary
ban.

### 10.5 Fixed neutral-proatom tail cutoff

The `0.2.0` numerical contract uses the fixed per-atom cutoff:

\[
\rho_c = 10^{-4}\ \mathrm{electron/bohr^3}.
\]

For every profile, define the unique cutoff radius:

\[
\rho_A(r_A^c)=\rho_c,
\qquad
\rho_B(r_B^c)=\rho_c.
\]

This is a model policy for ignoring weak neutral-proatom tails. It MUST NOT be
described as a universal lower bound for a chemically meaningful QTAIM bond
critical point.

The cutoff is applied to each component separately. Therefore a gap where both
components are below the cutoff can have a summed density below
`2 * rho_c`, not necessarily below `rho_c`.

The cutoff is fixed rather than user-configurable in `0.2.0`. It MUST be exposed
in result metadata and included in the pairwise numerical-contract identifier.

### 10.6 Shared result information

Use one small immutable result type for both direct functions and the dispatcher
unless implementation evidence strongly favors two types.

Preferred first design:

```python
@dataclass(frozen=True, slots=True)
class IASPositionResult:
    atom_a: str
    atom_b: str
    distance: float
    distance_unit: str
    density_unit: str
    requested_mode: str
    method: str
    status: str
    position_from_a: float | None
    position_from_b: float | None
    fraction_from_a: float | None
    rho_a: float | None
    rho_b: float | None
    rho_sum: float | None
    cutoff_density: float
    cutoff_radius_a: float
    cutoff_radius_b: float
    contour_separation: float
    alternative_position_from_a: float | None
    alternative_rho_sum: float | None
    relative_depth_gap: float | None
    search_resolution: float | None
    search_converged: bool | None
    dataset_id: str
    interpolation_contract: str
    pairwise_contract: str
```

The exact field list is preferred, not binding. The result MUST still expose:

1. the returned coordinate or an explicit absence;
2. requested mode and actual method;
3. status;
4. component and summed density at a returned coordinate;
5. cutoff, cutoff radii, and signed contour separation;
6. enough minimum-search diagnostics to interpret ambiguity when `mode` is
   `"minimum"`;
7. dataset, interpolation, and pairwise-contract provenance;
8. coordinate orientation.

Do not return one unexplained float.

### 10.7 Proatomic-boundary mode

Let the signed contour separation be:

\[
d_c=R-r_A^c-r_B^c.
\]

For a homonuclear pair, return exactly:

\[
x=R/2.
\]

Use status `low_density_gap` when its two cutoff contours are separated;
otherwise use the ordinary successful status. The coordinate remains `R/2` in
either regime.

For an unlike pair:

- if `d_c > 0`, the cutoff contours do not overlap. Return the midpoint of the
  two contour points:

  \[
  x=\frac{r_A^c+(R-r_B^c)}{2}
   =\frac{R+r_A^c-r_B^c}{2};
  \]

  use method `cutoff_gap_midpoint` and status `low_density_gap`;
- if the contours overlap or touch, solve the unique monotone equation:

  \[
  \rho_A(x)=\rho_B(R-x);
  \]

  use method `equal_proatom_density`;
- if an unlike atom dominates the entire interval and the equal-contribution
  equation has no interior solution, return no coordinate with status
  `one_atom_dominates`.

At `R=r_A^c+r_B^c`, the contour midpoint and equal-contribution definitions meet
at the same coordinate. The implementation SHOULD classify this as
`cutoff_contact` or otherwise make contact visible without changing the
coordinate.

### 10.8 Promolecular-minimum mode

This mode searches only the meaningful-overlap interval where both neutral
proatomic contributions are at least the cutoff:

\[
I_c=
\left[
\max(0,R-r_B^c),
\min(R,r_A^c)
\right].
\]

Binding behavior:

- for an unlike pair, if `I_c` is empty, return no minimum coordinate with
  status `low_density_gap`;
- for a homonuclear pair, return exactly `R/2` by symmetry, even if `I_c` is
  empty or the raw interpolant contains slightly lower symmetric off-center
  shell minima; retain `low_density_gap` as the status when applicable;
- for unlike pairs, find one **practically resolved** interior minimum of
  `f(x;R)` under Section 11’s fixed spatial-resolution contract;
- do not enumerate or expose every mathematical microminimum;
- retain at most the selected resolved valley and one materially competitive
  alternative;
- if no interior valley is resolved, return no coordinate with status
  `no_resolved_interior_minimum`;
- if a boundary value is lower than the selected interior valley, retain the
  candidate as a diagnostic but use status `boundary_dominated`;
- if two separated resolved valleys are practically competitive, return the
  deeper one and expose the runner-up and relative depth gap with status
  `ambiguous_competing_minima`;
- if the adaptive passes do not stabilize, return the finest-pass candidate
  with status `search_unstable` and `search_converged=False`.

The result MUST identify a homonuclear return as `homonuclear_midpoint`, not
mislabel it as a numerically discovered minimum when the midpoint fails the
resolved-valley check.

The following concepts from the superseded all-minima design are intentionally
absent from `0.2.0`:

- exhaustive local-minimum lists;
- exact global-tie enumeration;
- basin widths and watershed clipping;
- weighted averages of separate minima;
- high-precision reconstruction of sub-ULP event topology.

### 10.9 Why both modes are retained

`boundary` mode is the recommended production choice for geometry and weighted
Voronoi/Laguerre workflows because it is unique, continuous at cutoff contact,
symmetry-preserving, and inexpensive.

`minimum` mode is retained for Bader-oriented research and calibration because a
line-density minimum is a more direct promolecular analogue of an internuclear
critical-point coordinate. Its optional status and diagnostics make the model
limitations visible instead of hiding them behind an averaged coordinate.

Documentation SHOULD demonstrate both modes on the same pairs and MUST explain
that disagreement between them is a scientific-model difference, not
necessarily a numerical error.

### 10.10 Pair reversal and homonuclear symmetry

For a result on `(A, B, R)` and the reversed result `(B, A, R)`:

- a returned position `x` corresponds to `R-x`;
- method and status remain equivalent after A/B relabeling;
- component densities swap;
- summed density, cutoff regime, search convergence, relative depth gap, and
  practical ambiguity remain unchanged;
- an alternative minimum, when present, also transforms to `R-x_alt`;
- `one_atom_dominates` identifies the correspondingly relabeled atom.

For every homonuclear pair and every valid distance, both public modes return
exactly `R/2` after output-unit conversion within the ordinary conversion
rounding.

Canonical internal orientation MAY be used to make reversal invariance
structural.

### 10.11 Status and failure semantics

The exact vocabulary may be adjusted, but the result model MUST distinguish at
least:

```text
ok
low_density_gap
one_atom_dominates
no_resolved_interior_minimum
boundary_dominated
ambiguous_competing_minima
search_unstable
```

The method field MUST distinguish at least:

```text
homonuclear_midpoint
equal_proatom_density
cutoff_gap_midpoint
promolecular_density_minimum
none
```

Missing profiles return `None`. A scientifically non-applicable pair with valid
profiles returns a typed result with `position_from_a=None`; it is not treated
as missing data or an exception.

## 11. Pairwise numerical implementation decision

The earlier exact all-minima design is retained only as supporting numerical
research. Production Stage 4 uses the smaller contract below.

### 11.1 Shared profile preparation and cutoff radii

For every loaded profile, cache:

- logarithmic radii;
- logarithmic densities;
- ordinary log–log segment coefficients;
- the fixed `1e-4 electron/bohr^3` cutoff radius.

Because each packaged profile is strictly decreasing over its stored positive
segments, the cutoff radius is unique. Locate the bracketing stored values and
invert the accepted log–log segment analytically. Do not run a general root
finder for a cached one-dimensional inverse.

Dataset validation MUST confirm for every packaged H–Lr profile that:

- all positive segments are strictly decreasing;
- the first stored value is above the cutoff;
- the profile falls below the cutoff before the 20-bohr public limit;
- substituting the cached radius reproduces the cutoff within a documented
  floating-point tolerance.

### 11.2 Boundary-mode algorithm

1. Validate and convert `R` to bohr.
2. Apply canonical pair orientation if used.
3. Read the two cached cutoff radii.
4. For identical atoms, return `R/2` immediately.
5. If the cutoff contours have a positive gap, return their midpoint.
6. Otherwise solve

   \[
   g(x)=\log\rho_A(x)-\log\rho_B(R-x)=0.
   \]

   The function is monotone non-increasing under the packaged profile contract,
   so bracketed bisection is sufficient.
7. If the endpoint signs do not bracket a root, return
   `one_atom_dominates`.
8. Stop bisection when the coordinate bracket is no wider than `1e-10 bohr` or
   binary64 adjacency is reached.
9. Evaluate and report component densities using the public Stage 3 profile
   convention at the selected coordinate.
10. Transform orientation and units only after the native result is complete.

Use the continuous log–log segment representation for the equality comparison.
One-ULP exact-knot value round trips MUST NOT create or remove an equality
crossing.

### 11.3 Practical minimum-mode algorithm

The search is intentionally resolution-limited. Its public spatial resolution
is:

```text
IAS_MINIMUM_RESOLUTION_BOHR = 0.01
```

This is approximately `0.0053 angstrom`, far below the intended chemical-geometry
scale while large enough to coalesce the sub-resolution shell and interpolation
splittings that made exhaustive Stage 4A disproportionately complex.

For unlike atoms with a nonempty significant-overlap interval `I_c`:

1. Evaluate `f(x;R)` on a deterministic uniform grid over `I_c` with step no
   larger than `0.02 bohr`. Include both interval endpoints, the interval
   midpoint, and the equal-proatom-density coordinate when it exists.
2. A sample-resolved valley is an interior sample no higher than its immediate
   neighbors.
3. Refine each sampled valley only inside its neighboring sample bracket with a
   small dependency-free bounded minimizer. Golden-section search is acceptable
   because the bracket is already local and the public contract coalesces
   smaller internal structure.
4. Repeat with step no larger than `0.01 bohr`.
5. Combine candidates from both passes. Candidates closer than `0.01 bohr`
   belong to one resolved valley; retain the lowest sampled/refined value as
   that valley’s representative.
6. If the selected resolved valley changes by more than `0.01 bohr`, or its
   density changes by more than `1e-4` relative, run one fallback pass with step
   no larger than `0.005 bohr`.
7. After the fallback, return the finest supported representative and set
   `search_converged` according to the same practical criteria. Do not invoke
   Decimal arithmetic merely to classify smaller structure.
8. Sort resolved valleys by density. Retain the selected valley and at most one
   runner-up separated by at least `0.01 bohr`.
9. Mark `ambiguous_competing_minima` when the runner-up is within `1e-4`
   relative density of the selected valley. This is a declared practical
   equivalence policy, not a binary64 equality tolerance.
10. Compare `f(0)` and `f(R)` with the selected interior value. If either is
    lower by more than the ordinary floating-point comparison envelope, use
    `boundary_dominated`.

For a homonuclear pair, return `R/2` without running this search. The
implementation MAY evaluate nearby samples to report whether the midpoint also
behaves as a resolved minimum, but this diagnostic MUST NOT move the returned
coordinate.

If no interior valley is found on the finest pass, return
`no_resolved_interior_minimum`. Do not clamp a minimum to a cutoff endpoint or
nucleus.

### 11.4 Tolerance categories

Keep these concepts separate:

- **tail cutoff:** `1e-4 electron/bohr^3`; a fixed model policy;
- **minimum spatial resolution:** `0.01 bohr`; a fixed practical-resolution
  policy;
- **competitive depth gap:** `1e-4` relative; a user-visible ambiguity policy;
- **equality bisection tolerance:** `1e-10 bohr`; a numerical convergence
  tolerance;
- **ordinary floating-point envelope:** only for comparisons whose outcome is
  not already defined by the practical policies above.

Do not reuse one large `isclose` tolerance for cutoff contact, equality,
minimum competition, and binary64 roundoff. Do not tune tolerances only to make
individual examples pass.

### 11.5 No exact-knot or all-minima machinery in production

The production algorithm MUST NOT add:

- an exact Decimal event sweep;
- exhaustive one-sided derivative topology;
- sub-ULP cell reconstruction;
- proximity merging of mathematical basins;
- global-tie lists;
- watershed-width construction;
- weighted averaging across minima.

Exact profile knots are ordinary samples under the Stage 3 evaluator. A
sub-resolution feature that changes only under exact-event reconstruction is
outside the declared `minimum`-mode resolution and cannot affect
`boundary` mode.

The archived Stage 4A design and review cases remain useful as a conservative
development reference and as supporting information explaining this decision.

### 11.6 Performance guardrail

The intended downstream use includes repeated pair evaluation.

Record local, non-CI timings for:

- first call including data load;
- cached cutoff-radius access;
- one `boundary` pair;
- one ordinary `minimum` pair;
- one fallback-pass `minimum` pair;
- a deterministic 1,000-pair batch in each mode.

Targets on the recorded development machine are:

```text
cached boundary mode: comfortably below 0.2 ms/pair
cached minimum mode:  comfortably below 1.0 ms/pair in the ordinary case
```

These are design targets, not portable CI thresholds. No benchmarking or
numerical runtime dependency may be added.

### 11.7 Validation reference and supporting study

Stage 4 validation MUST use two references for different purposes:

1. a slower fine-grid-and-refinement search inside `I_c` to validate the
   practical minimum contract at and above `0.01 bohr` resolution;
2. the archived exact-event Stage 4A cases to confirm that intentionally omitted
   microstructure cannot change boundary mode and is either coalesced or
   reported as unresolved/ambiguous in minimum mode.

The executed notebook:

```text
notebooks/04-ias-method-selection-study.ipynb
```

and its compact documentation page MUST record:

- cutoff-radius coverage for H–Lr;
- representative boundary/minimum comparisons;
- homonuclear Li–Li behavior;
- low-density-gap behavior;
- practical-reference agreement and timings;
- the numerical pathologies that motivated abandoning exhaustive all-minima
  production semantics;
- the final two-mode decision and limitations.

Agreement with actual molecular-density QTAIM coordinates is scientifically
valuable and SHOULD be added when a curated benchmark is available. It is not a
claim made by `0.2.0`, and absence of such a benchmark must remain explicit in
the documentation.

## 12. Documentation and notebook strategy

### 12.1 Split feature documentation from the later overhaul

`0.2.0` must contain enough documentation to use the new API safely:

- accurate public docstrings for new objects;
- one concise density/pairwise-boundary guide or equivalent section;
- exact provenance, units, range, cutoff, mode semantics, and limitations;
- one executed Stage 4 method-selection notebook;
- one executed user-facing feature notebook with plots;
- a changelog entry and working README mention.

The broad documentation redesign belongs to `0.2.1` after the API is accepted.

Do not move the README marketing rewrite, complete existing-notebook rewrite,
or all-module docstring conversion into the critical path of `0.2.0`.

### 12.2 `0.2.0` Stage 4 supporting notebook is mandatory

Add and execute:

```text
notebooks/04-ias-method-selection-study.ipynb
```

This notebook is supporting information for the numerical and scientific
decision. It MUST:

- clearly label all helper functions as research prototypes rather than public
  API;
- explain the fixed per-atom cutoff;
- compare `boundary` and `minimum` definitions;
- reproduce representative cases and practical timings;
- summarize the archived exact all-minima failure modes;
- explain why exhaustive all-minima enumeration is not the production default;
- state that neither mode is an exact QTAIM surface;
- be linked from a compact page at `docs/dev/ias_method_selection.md`.

Saved plots are encouraged. Matplotlib may be an optional
notebook/documentation dependency and MUST NOT become a runtime dependency.

### 12.3 `0.2.0` feature notebook is mandatory

Add:

```text
notebooks/05-proatomic-density-and-ias.ipynb
```

The committed feature notebook MUST:

- be executed;
- contain saved execution counts;
- contain saved text and plot outputs;
- execute from top to bottom in a clean environment;
- use short Markdown explanations before every logical code section;
- explain what the reader should notice rather than merely restating the code;
- avoid hidden state and manual edits to outputs;
- use deterministic examples where practical.

Required content:

1. package and dataset discovery through `get_builtin_set()` and registry
   metadata;
2. profile retrieval and scalar evaluation with independent radius/density
   units;
3. one or two radial-density plots, preferably with a logarithmic density axis;
4. one ordinary heteronuclear `boundary` example;
5. the same pair in `minimum` mode;
6. a plot of `rho_A(x)`, `rho_B(R-x)`, and their sum;
7. a homonuclear midpoint example;
8. a low-density-gap example;
9. one no-resolved-minimum or one-atom-dominance example;
10. a concise limitations and mode-selection section.

For `0.2.0`, the notebooks may be linked from the docs/GitHub even if the
current Markdown exporter cannot faithfully embed rich plot output. The saved
`.ipynb` files remain the source artifacts.

### 12.4 Current notebook behavior to replace in `0.2.1`

The current repository tools:

- execute code cells in a plain Python namespace;
- suppress or separately capture stdout;
- do not write execution counts or outputs into `.ipynb`;
- do not verify that committed outputs are current;
- export duplicate Markdown pages;
- do not preserve rich Jupyter output such as Matplotlib figures.

They do not “unexecute” notebooks; they simply ignore the stored execution
state and run code transiently.

`0.2.1` should replace this with actual Jupyter-kernel execution.

Preferred compact workflow:

1. one maintainer tool, preferably the existing `tools/check_notebooks.py`,
   gains:
   - `--write` to execute notebooks and save normalized outputs;
   - `--check` to execute into temporary files and compare against committed
     normalized notebooks;
2. use `nbclient`/`nbconvert` and `nbformat`, not `exec()` of extracted code
   strings;
3. normalize nondeterministic execution metadata before comparison;
4. fail on cell errors;
5. keep outputs committed;
6. CI verifies that outputs are fresh.

Avoid adding separate “execute,” “export,” and “check” tools when one tool with
two modes is sufficient.

### 12.5 Direct notebook rendering in `0.2.1`

Preferred documentation approach:

- render actual `.ipynb` files directly with `mkdocs-jupyter`;
- use committed saved outputs;
- set documentation-build execution off, because freshness is checked
  separately;
- include notebook source/download links;
- remove `docs/notebooks/*.md`;
- remove `tools/export_notebooks.py`;
- remove export-sync tests and replace them with notebook execution-state tests.

This reduces duplicated files and allows plots and rich outputs to appear
naturally.

A different direct-rendering solution may be used if it is materially better,
but do not keep both direct rendering and generated Markdown copies.

### 12.6 Explanatory notebook writing standard

Every shipped notebook should contain:

- a title and a concise goal;
- prerequisites or expected knowledge;
- Markdown before each meaningful code section;
- explanation of important output after or before the cell;
- section headings that form a useful table of contents;
- a final “what this demonstrated” and limitations section.

Not every one-line import needs its own essay. The standard is that a reader
should understand why each logical block exists and what to inspect in its
output.

### 12.7 Full API reference with MkDocs

Do not switch away from MkDocs solely to obtain Sphinx-like API pages.

The existing `mkdocstrings[python]` stack can render:

- complete function and method signatures;
- type annotations;
- parameter names, types, descriptions, and defaults;
- return types and descriptions;
- raised exceptions;
- class attributes;
- examples and cross-references.

The `0.2.1` task is to configure and feed it correctly.

Preferred `mkdocs.yml` options include:

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: google
            show_root_heading: true
            show_source: false
            show_signature: true
            separate_signature: true
            show_signature_annotations: true
            signature_crossrefs: true
            annotations_path: brief
            show_docstring_parameters: true
            show_docstring_returns: true
            show_docstring_raises: true
            show_docstring_attributes: true
            show_docstring_examples: true
```

Exact presentation options may be tuned after inspecting the rendered site.

All intended public functions, classes, methods, and dataclass attributes should
receive structured Google-style docstrings with, as applicable:

```text
Args:
Returns:
Raises:
Attributes:
Examples:
Notes:
```

Type annotations remain the source of type information; docstrings explain
meaning, units, behavior, and constraints.

### 12.8 README/home-page redesign in `0.2.1`

`docs/index.md` remains the source of `README.md`.

The home page should immediately answer:

1. What is `atomref`?
2. Which scientific/software problems does it solve?
3. Why use it instead of embedding constants or ad hoc tables?
4. What can a user do in the first five lines of Python?
5. Which data and provenance guarantees are provided?

The opening should communicate an identity close to:

> `atomref` provides cited atomic values and frozen spherical free-atom
> electron densities through a small Python API for crystallographic,
> quantum-chemical, and molecular-structure algorithms.

Show working radii, profile, boundary-mode, and minimum-mode examples near the top. Move detailed policy
terminology and nested-transfer mechanics lower.

Avoid leading with negative positioning such as “not another periodic-table
encyclopedia.”

### 12.9 Keep the durable docs compact

The preferred durable structure after `0.2.1` is still small:

```text
docs/index.md
docs/guide/proatomic_density.md
docs/dev/architecture.md
docs/api/*.md
notebooks/*.ipynb
```

Remove the duplicated public development-plan page. Do not create separate pages
for interpolation, pairwise method semantics, provenance, licensing, and every result
field unless one combined guide becomes genuinely difficult to use.

## 13. Staged implementation plan

## `0.2.0` implementation

### Stage 0 — Baseline verification

#### Goal

Confirm the supplied repository is healthy before modifying it.

#### Actions

Inspect at minimum:

- `src/atomref/registry.py`;
- `src/atomref/policy.py`;
- `src/atomref/__init__.py`;
- `src/atomref/data/registry.json`;
- package-data configuration;
- registry, public-API, package-data, and release tests;
- existing notebooks and notebook tools;
- `mkdocs.yml`.

Record:

- current version;
- baseline tests;
- current public API;
- current built-in dataset return type;
- current notebook execution/output state.

Run:

```bash
python -m pytest -q
python tools/check_registry.py
python tools/check_notebooks.py
python tools/export_notebooks.py --check
python tools/gen_readme.py --check
```

When dependencies are available:

```bash
flake8 src tests tools
mkdocs build --strict
```

#### Constraints

- Do not change code in Stage 0.
- Report baseline failures before attributing later failures to new work.

#### Completion criteria

- baseline recorded;
- relevant call graph understood;
- no unexplained existing failures.

#### Suggested commit

No commit.

---

### Stage 1 — Generalize packaged-dataset loading

#### Goal

Make `get_builtin_set()` the unified entry point for scalar and radial packaged
datasets before adding the new data.

#### Required changes

1. Add an explicit storage-kind discriminator to existing registry entries.
2. Add the radial storage kind to registry validation.
3. Introduce the minimal loaded radial-set type.
4. Change `get_builtin_set()` to dispatch by storage kind.
5. Preserve caching and alias resolution.
6. Narrow scalar policy and convenience code explicitly to
   `ElementScalarSet`.
7. Update type annotations, public exports, tests, and architecture comments.
8. Generalize `CoverageInfo` wording.

#### Required tests

- every existing scalar dataset still loads through `get_builtin_set()`;
- the returned scalar type remains `ElementScalarSet`;
- aliases still resolve before caching/loading;
- an unknown storage kind raises `DatasetError`;
- scalar policy code rejects a radial test fixture clearly;
- generic discovery/metadata functions do not care about payload kind;
- a small synthetic radial fixture can be dispatched and queried;
- existing scalar policy results are unchanged.

#### Do not do

- do not add radial policy behavior;
- do not generalize transfer fitting;
- do not build a registry framework beyond the two actual storage kinds;
- do not bypass `get_builtin_set()` from the later proatomic API.

#### Completion criteria

- generic built-in dataset dispatch is working;
- scalar behavior is unchanged;
- radial sets can participate in the same discovery and loading path.

#### Suggested commit

```text
refactor: generalize built-in dataset loading
```

---

### Stage 2 — Reproducible neutral profile snapshot

#### Goal

Add the exact minimal neutral H–Lr data product without runtime dependence on
the generator project.

#### Required changes

1. Add `tools/build_proatomic_density_snapshot.py`.
2. Add one compressed package-data file.
3. Add the `proatomic_density` quantity and dataset metadata to `registry.json`.
4. Update `NOTICE.md` with CC BY attribution and exact DOIs.
5. Update package build inclusion for `.zip`.
6. Extend registry, package-data, and distribution checks.
7. Add focused source/data-integrity tests.
8. Document the maintainer tool briefly in `tools/README.md`.

#### Why the builder belongs in `tools/`

This script is not for normal package users. It is a maintainer tool that makes
the committed scientific snapshot auditable and reproducible.

Without it, future maintainers and agents would have to trust an opaque
hand-edited compressed table and manually repeat:

- hash verification;
- neutral-state selection;
- H–Lr coverage checks;
- 20-bohr truncation/bracketing;
- column ordering;
- deterministic compression.

The script should therefore be named as a snapshot builder, not as a public
“import” feature.

#### Snapshot-builder requirements

The builder MUST:

- accept a local upstream dataset directory or explicit CSV/metadata paths;
- perform no network access;
- verify source hashes and identities;
- select exactly one neutral profile per Z=1..103 from metadata;
- preserve source radius and density decimal values;
- retain rows through the first source point above 20 bohr;
- verify expected retained row count and bracketing values;
- verify finite, strictly increasing positive radii;
- verify finite, strictly positive densities in the retained table;
- verify every profile is monotonically non-increasing within a documented
  numerical tolerance;
- write columns in increasing Z order;
- create the deterministic single-member ZIP defined in Section 6.6;
- support a check mode and a write mode;
- print a concise source/output summary.

Preferred commands:

```bash
python tools/build_proatomic_density_snapshot.py \
  --source-dir ../atomref-proatoms/data/profiles/pbe0_sfx2c_dyallv4z_h-lr_spherical_v2 \
  --write

python tools/build_proatomic_density_snapshot.py \
  --source-dir ../atomref-proatoms/data/profiles/pbe0_sfx2c_dyallv4z_h-lr_spherical_v2 \
  --check
```

The CLI may be simplified.

#### Registry requirements

Add one quantity:

```text
proatomic_density
```

Add one atomref-side set ID clearly identifying:

- neutral scope;
- H–Lr coverage;
- PBE0/sf-X2C/dyall-v4z;
- upstream v2 lineage.

The exact ID remains a review point.

Its storage metadata MUST declare `element_radial_csv_zip`, filename
`proatomic_density_neutral.zip`, and member
`proatomic_density_neutral.csv`.

The new dataset MUST load through:

```python
get_builtin_set(DatasetRef("proatomic_density", set_id))
```

and return the radial loaded-set type.

#### Data tests

Tests MUST verify:

- the compressed file is packaged;
- exactly 103 profile columns exist;
- columns map to Z=1..103 without gaps;
- row count is 1127;
- radii are strictly increasing;
- the retained bracketing point is above 20 bohr;
- all densities are finite and positive;
- all profiles are monotone non-increasing within tolerance;
- source and license metadata are present;
- generic `get_builtin_set()` loads the radial set;
- wheel and sdist contain the data and attribution metadata.

Source-dependent byte regeneration may be a maintainer check when the upstream
archive is not present in CI. CI must validate the committed snapshot
internally.

#### Do not do

- do not package all 501 states;
- do not package the full upstream metadata;
- do not package configurations or multiplicities;
- do not add the upstream generator as a dependency;
- do not download data at runtime;
- do not add a second registry.

#### Completion criteria

- reproducible neutral snapshot committed;
- generic dataset loader returns it;
- provenance and licensing recorded;
- distribution tests pass.

#### Suggested commit

```text
feat(data): add neutral proatomic density snapshot
```

---

### Stage 3 — Proatomic density evaluation

#### Goal

Expose a small typed dependency-free profile API with stable interpolation and
independent units.

#### Required changes

1. Add `src/atomref/proatoms.py`.
2. Add immutable profile access/evaluation objects or an equally clear API.
3. Use the radial object returned by `get_builtin_set()`.
4. Implement radius and density unit conversion independently.
5. Implement the interpolation contract.
6. Add lazy/shared cached numerical data as needed.
7. Add public exports and public-API tests.
8. Add density tests.
9. Add minimum accurate API docstrings and feature documentation.

#### Density acceptance tests

##### Dataset and profile access

- H, C, O, Fe, La, U, and Lr profiles load.
- Rf and Og return `None`.
- D and T produce the H profile.
- invalid symbols return `None`.
- aliases/set IDs resolve through registry conventions.
- repeated calls reuse cached set/profile data.
- the public profile/set objects cannot mutate shared package data.

##### Radius behavior

- `r=0` equals the first stored value.
- `r=r_min` equals the exact stored value.
- selected interior knots reproduce exact source values.
- `r=20 bohr` evaluates successfully.
- values above 20 bohr raise.
- negative, `NaN`, and infinite radii raise.
- unknown radius units raise.

##### Interpolation

- a synthetic power-law profile is reproduced by log–log interpolation;
- interpolation is continuous at stored knots within tolerance;
- interpolated densities remain positive;
- representative profiles remain non-increasing;
- no linear fallback or zero-fill path exists in the supported domain.

##### Units

- equivalent bohr/ångström coordinates evaluate the same physical point;
- electron/bohr³ and electron/Å³ outputs convert correctly;
- default radius unit is ångström;
- default density unit is electron/bohr³;
- changing density unit does not change interval selection or provenance;
- unknown density units raise.

##### Compatibility

- all existing scalar tests pass unchanged;
- `get_radii_set()` and `get_xh_set()` retain scalar return types;
- policy code rejects radial sets explicitly;
- all packaged sets remain accessible through `get_builtin_set()`.

#### Completion criteria

- density evaluation works for neutral H–Lr;
- unit, range, and interpolation behavior is tested;
- API is typed and documented;
- runtime remains dependency-free.

#### Suggested commit

```text
feat: add proatomic density evaluation
```

---

### Stage 4 — Pairwise proatomic boundary and practical IAS proxy

#### Goal

Implement the two-mode pairwise contract from Sections 10 and 11 without the
superseded exhaustive all-minima machinery.

#### Stage 4A — finalize and preserve the numerical decision

Before public implementation:

1. accept the revised Sections 10 and 11;
2. retain the archived exact-event Stage 4A reports as development evidence,
   not as the production contract;
3. add and execute `notebooks/04-ias-method-selection-study.ipynb`;
4. add `docs/dev/ias_method_selection.md` and link the notebook;
5. verify all H–Lr cutoff radii and the monotonicity assumptions;
6. record representative agreement and timing for the practical minimum search;
7. resolve final public function/result names without changing the two-mode
   semantics.

Stage 4A MUST NOT modify production pairwise code beyond documentation/test
fixtures needed to preserve the decision record.

Representative development pairs should include:

```text
H-H
Li-Li
C-O
Fe-O
H-U
H-heavy-element
one low-density-gap pair
one one-atom-dominance pair
one boundary-dominated minimum case
one pair with competing resolved minima
one archived sub-resolution exact-event case
```

#### Stage 4B — implement shared result, direct functions, and dispatcher

Implement:

- the fixed cached cutoff radius;
- the shared immutable result type;
- `estimate_proatomic_boundary()`;
- `estimate_promolecular_density_minimum()`;
- `estimate_ias_position(..., mode="boundary" | "minimum")`;
- exact homonuclear midpoint handling;
- equal-contribution bisection;
- cutoff-gap midpoint behavior;
- the resolution-limited minimum search;
- explicit statuses and provenance;
- canonical reversal handling and unit conversion.

Do not implement:

- exhaustive local-minimum enumeration;
- exact global-tie machinery;
- widths or watershed clipping;
- weighted centers or spreads;
- Decimal event topology;
- a universal minimum-distance ban;
- hidden fallback between modes.

#### Stage 4C — validation

Required tests cover:

- all H–Lr cutoff radii are unique, finite, and reproduce the cutoff;
- exact homonuclear `R/2` in both modes;
- equal component densities in ordinary boundary-overlap cases;
- cutoff-gap midpoint geometry;
- continuous agreement of the two boundary branches at cutoff contact;
- explicit one-atom dominance;
- minimum search limited to the significant-overlap interval;
- practical-reference agreement at the declared `0.01 bohr` resolution;
- no-resolved-minimum, boundary-dominated, competing-minimum, and unstable-search
  statuses;
- pair reversal for both primary and alternative coordinates;
- distance-unit and density-unit invariance;
- invalid mode, distance, and units;
- missing elements;
- representative light, transition, lanthanide, and actinide pairs;
- practical cached performance for both modes;
- regression cases from the Stage 4A supporting study.

#### Completion criteria

- the default returns a stable, interpretable proatomic divider;
- the optional mode returns one cutoff-bounded, practically resolved
  promolecular minimum or an explicit non-result/diagnostic status;
- identical atoms always return `R/2`;
- no arbitrary short-distance ban is present;
- pair reversal, units, cutoff, provenance, and failures are tested;
- no exact molecular-QTAIM claim is made;
- no all-minima production machinery remains in scope.

#### Suggested commit

```text
feat: add two-mode proatomic IAS position estimates
```

### Stage 5 — Executed feature notebook and `0.2.0` release

#### Goal

Demonstrate the accepted functionality, complete minimum documentation, and
release `0.2.0` without performing the full documentation overhaul.

#### Required notebook work

Add and execute:

```text
notebooks/05-proatomic-density-and-ias.ipynb
```

It MUST satisfy Section 12.3.

For `0.2.0`, extend existing notebook validation minimally so CI verifies:

- the notebook exists;
- all nonempty code cells have execution counts;
- expected output-bearing cells contain saved outputs;
- the code executes cleanly;
- required Markdown sections are present.

Do not build a second large notebook pipeline during this stage.

#### Minimum documentation

- add the new notebook to the notebook overview;
- link the saved notebook from docs;
- add accurate density, cutoff, mode-selection, and IAS-proxy guide material;
- add the new module API page;
- mention the feature on the home page without the full marketing rewrite;
- document exact provenance, units, 20-bohr domain, and limitations;
- update architecture only where needed for generic datasets;
- update changelog and release metadata.

#### Project metadata

Update:

- version to `0.2.0`;
- package keywords for proatomic density/electron density/IAS;
- build inclusion for `.zip`;
- installed-wheel smoke tests.

#### Installed-wheel smoke test

At minimum:

```python
import atomref as ar

ref = ar.DatasetRef("proatomic_density", "<set-id>")
dataset = ar.get_builtin_set(ref)

rho = ar.get_proatomic_density(
    "O",
    0.75,
    radius_unit="angstrom",
    density_unit="electron/bohr^3",
)
assert rho is not None and rho > 0

boundary = ar.estimate_proatomic_boundary("C", "O", 1.43)
assert boundary is not None and boundary.position_from_a is not None

minimum = ar.estimate_promolecular_density_minimum("C", "O", 1.43)
assert minimum is not None

result = ar.estimate_ias_position("C", "O", 1.43, mode="boundary")
assert result == boundary
```

#### Final commands

Run all current checks, including:

```bash
python tools/check_registry.py
python tools/check_notebooks.py
python tools/export_notebooks.py --check
python tools/gen_readme.py --check
flake8 src tests tools
python -m pytest -q
mkdocs build --strict
python tools/release_check.py
```

If the feature notebook is not compatible with the current Markdown exporter
because it contains plots, the exporter may omit that notebook for `0.2.0` while
the docs link directly to the saved `.ipynb`. Record this temporary state for
Stage 6 rather than implementing a plot-specific Markdown exporter.

#### Completion criteria

- all `0.2.0` acceptance criteria pass;
- feature notebook is executed and saved;
- wheel/sdist work;
- minimal docs are accurate;
- no broad docs rewrite has obscured scientific review.

#### Suggested commits

```text
docs: add IAS method study and proatomic density feature notebook
chore: prepare atomref 0.2.0
```

---

## `0.2.1` documentation and discoverability work

Do not start these stages until `0.2.0` is accepted.

### Stage 6 — Notebook infrastructure and content overhaul

#### Goal

Make notebooks true executable documentation with saved, verifiable rich
outputs while reducing duplicate files and tools.

#### Required changes

1. Add notebook/documentation optional dependencies:
   - `nbformat`;
   - `nbclient` or `nbconvert`;
   - `ipykernel`;
   - `matplotlib`;
   - `mkdocs-jupyter`.
2. Rewrite one existing notebook tool to support execution/update/check modes.
3. Execute and save all notebooks.
4. Add explanatory Markdown before every logical code section.
5. Render actual `.ipynb` files directly in MkDocs.
6. Remove generated `docs/notebooks/*.md`.
7. Remove `tools/export_notebooks.py`.
8. Remove export-sync tests and CI steps.
9. Add normalized execution-freshness checks.
10. Ensure plots render on the documentation site.

#### Preferred command model

```bash
python tools/check_notebooks.py --write
python tools/check_notebooks.py --check
```

The exact name may remain `check_notebooks.py` even though write mode is
supported, to avoid another file.

#### Completion criteria

- every notebook is executed and saved;
- re-execution reproduces committed normalized outputs;
- plots are visible in MkDocs;
- no generated Markdown notebook copies remain;
- notebook prose is suitable for learning, not only smoke testing;
- the number of notebook tools/files is reduced.

#### Suggested commit

```text
docs: make notebooks executable documentation
```

---

### Stage 7 — Complete API docs, README, and `0.2.1` release

#### Goal

Make the documentation immediately useful to both new users and developers.

#### Required changes

1. Configure `mkdocstrings` for full typed signatures and structured sections.
2. Rewrite all intended public docstrings in one consistent style.
3. Verify every public parameter, return value, raised error, unit, and
   important attribute appears in rendered API docs.
4. Review API page member selection.
5. Rewrite `docs/index.md` for product positioning and regenerate `README.md`.
6. Improve quickstart flow.
7. Remove `docs/dev/dev_plan.md` and its navigation item.
8. Ensure architecture and data-curation docs match the final code.
9. Update changelog and version to `0.2.1`.
10. Simplify CI commands after removing notebook Markdown export.

#### API documentation acceptance

For every public function/class added or retained:

- signature is visible;
- annotations are visible;
- parameters include type, meaning, and default;
- return value is described;
- raised errors are described;
- units and valid ranges are explicit where relevant;
- dataclass attributes are visible;
- examples are present for non-obvious APIs;
- cross-references work.

#### README acceptance

A new visitor should discover within the initial screen:

- the package purpose;
- radii, profile, and IAS capabilities;
- the dependency-free runtime;
- a compact working example;
- provenance as a central value;
- links to installation, notebooks, datasets, and API.

#### Final checks

```bash
python tools/check_registry.py
python tools/check_notebooks.py --check
python tools/gen_readme.py --check
flake8 src tests tools
python -m pytest -q
mkdocs build --strict
python tools/release_check.py
```

#### Suggested commits

```text
docs: complete typed API reference
docs: reposition atomref documentation
chore: prepare atomref 0.2.1
```

## 14. Release acceptance checklists

### 14.1 `0.2.0` scope and compatibility

- [ ] Version is `0.2.0`.
- [x] Existing `0.1.x` public APIs remain available.
- [x] Existing scalar values and default policies are unchanged.
- [x] Runtime dependencies remain empty.
- [x] Runtime performs no network access.
- [x] No ionic or profile-correlation behavior is exposed.
- [x] `get_builtin_set()` loads every packaged scalar and radial dataset.
- [x] Scalar policy code rejects radial sets clearly.
- [x] Registry discovery and metadata work identically across payload kinds.

### 14.2 `0.2.0` data

- [x] Source profiles hash matches the pinned `profiles.csv`.
- [x] Source metadata hash matches the pinned `metadata.json`.
- [x] Upstream dataset ID and version match.
- [x] Basis ID and basis hash match.
- [x] Exactly 103 neutral profiles are selected.
- [x] Coverage is exactly Z=1..103.
- [x] Retained row count is 1127.
- [x] Public limit is exactly 20 bohr.
- [x] First retained point above 20 bohr brackets the endpoint.
- [x] All retained densities are finite and positive.
- [x] All retained profiles are monotone non-increasing within tolerance.
- [x] ZIP output satisfies the deterministic single-member contract in Section
      6.6.
- [x] Snapshot is built by the maintainer tool, not hand-edited.
- [x] Wheel and sdist contain `proatomic_density_neutral.zip`.
- [x] Registry and notice contain CC BY attribution and exact DOIs.

### 14.3 `0.2.0` density API

- [ ] Profile retrieval works for H–Lr.
- [ ] D/T map to H.
- [ ] Unsupported elements return `None`.
- [ ] Radius units and density units are independent.
- [ ] Default radius unit is ångström.
- [ ] Default density unit is electron/bohr³.
- [ ] Electron/Å³ output is available explicitly.
- [ ] `r=0` uses the first-grid value.
- [ ] Exact knots reproduce stored values.
- [ ] Positive-segment log–log interpolation is tested.
- [ ] `r=20 bohr` is valid.
- [ ] `r>20 bohr` raises.
- [ ] Negative and non-finite radii raise.
- [ ] Loading is lazy/cached through generic dataset machinery.
- [ ] Shared package data cannot be mutated through public objects.

### 14.4 `0.2.0` pairwise boundary and IAS-proxy API

- [ ] Distance is measured from A toward B and documented.
- [ ] Distance must be `0 < R <= 20 bohr`.
- [ ] Distance and density units are independent.
- [ ] The fixed per-atom cutoff is `1e-4 electron/bohr^3` and is reported.
- [ ] Every packaged H–Lr profile has one validated cutoff radius.
- [ ] `estimate_proatomic_boundary()` is available.
- [ ] `estimate_promolecular_density_minimum()` is available.
- [ ] `estimate_ias_position()` dispatches explicitly by mode.
- [ ] The default mode is `boundary`.
- [ ] `minimum` mode never silently falls back to `boundary`.
- [ ] Identical atoms return exactly `R/2` in both modes.
- [ ] Overlapping unlike atoms can return the equal-proatom-density divider.
- [ ] Separated cutoff contours return their geometric midpoint in boundary mode.
- [ ] Cutoff contact is continuous.
- [ ] One-atom dominance is explicit.
- [ ] Minimum search is confined to the significant-overlap interval.
- [ ] Minimum search uses the declared `0.01 bohr` practical resolution.
- [ ] At most one selected minimum and one competitive alternative are exposed.
- [ ] Low-density-gap, no-resolved-minimum, boundary-dominated, competing, and
      unstable cases are explicit.
- [ ] Density-unit conversion does not change geometry, method, or status.
- [ ] Pair reversal transforms primary and alternative positions correctly.
- [ ] Missing profiles return `None`.
- [ ] Invalid distances, modes, and units raise.
- [ ] Dataset, interpolation, cutoff, and pairwise-contract provenance is present.
- [ ] Practical minimum results agree with an independent slower search at the
      declared resolution.
- [ ] The API does not claim an exact QTAIM surface or critical point.
- [ ] Exhaustive local-minimum, tie, width, and weighted-center machinery is not
      part of the production API.

### 14.5 `0.2.0` notebook and packaging

- [ ] Stage 4 method-selection supporting notebook exists.
- [ ] Supporting notebook is executed and saved with outputs.
- [ ] Supporting notebook is linked from `docs/dev/ias_method_selection.md`.
- [ ] Proatomic density/pairwise feature notebook exists.
- [ ] Feature notebook is executed and saved with outputs.
- [ ] Both notebooks contain explanatory Markdown before logical code sections.
- [ ] The notebooks contain informative plots where appropriate.
- [ ] The feature notebook demonstrates both modes, homonuclear symmetry, a
      low-density gap, and an explicit non-ordinary case.
- [ ] Notebook execution is deterministic and validated.
- [ ] Minimal public docs describe source, units, range, cutoff, mode selection,
      and limitations.
- [ ] README is regenerated and mentions the feature accurately.
- [ ] Installed wheel loads the radial set, evaluates density, and performs both
      pairwise modes.

### 14.6 `0.2.1` notebook documentation

- [ ] All shipped notebooks are executed and saved.
- [ ] Re-execution freshness is checked through a Jupyter kernel.
- [ ] Notebook plots and rich outputs render directly in MkDocs.
- [ ] Logical code sections have explanatory Markdown.
- [ ] Generated notebook Markdown copies are removed.
- [ ] The separate notebook exporter is removed.
- [ ] One maintained notebook tool handles update and check modes.
- [ ] CI and docs workflows use the simplified process.

### 14.7 `0.2.1` API and README documentation

- [ ] Full typed signatures render.
- [ ] All public parameters, defaults, returns, raises, and attributes render.
- [ ] Public docstrings use one structured style.
- [ ] API cross-references work.
- [ ] README/home page explains value immediately.
- [ ] Working radii, density, boundary-mode, and minimum-mode examples appear near the top.
- [ ] Detailed policy terminology is moved below first-use content.
- [ ] Duplicate development-plan docs are removed.
- [ ] Strict docs and full release checks pass.

## 15. Optional architecture review after `0.2.0`

Do not implement this section automatically during the feature release.

After the density and IAS core is accepted, review actual friction encountered.

Possible small follow-up work only when justified by evidence:

- replace the hard-coded `[None] * 119` scalar allocation with a size derived
  from the element table;
- improve storage-kind validation if Stage 1 reveals weak points;
- add a static type-checking CI job;
- optimize repeated pairwise boundary/minimum evaluation if profiling shows a bottleneck;
- add scalar batch evaluation if downstream use proves it necessary;
- improve mixed-license artifact checks.

If generic `get_builtin_set()` dispatch could not be completed in `0.2.0`, that
becomes the highest-priority architecture task before expanding the profile API.
A temporary bypass must not silently become permanent.

Do not schedule a refactor release merely because it was anticipated. If the
feature integrates cleanly, complete `0.2.1` docs and stop.

## 16. Future compatibility and non-actionable roadmap

Everything in this section is for future reference. An agent implementing
`0.2.0` or `0.2.1` MUST NOT begin this work without an explicit scope change.

### 16.1 Ions and additional atomic properties

The initial radial dataset is neutral only.

To avoid blocking future ionic datasets:

- keep dataset identity explicit;
- state charge scope in metadata;
- do not imply that one profile per element is universal;
- do not encode state selection into the element parser;
- allow a later keyword-only dataset/state selector without breaking current
  calls;
- preserve the ability for a radial set to have a richer key model in a future
  release.

Do not add now:

- a `charge` argument that only accepts zero;
- an unused `AtomicStateKey` class;
- ionic configuration metadata copied from upstream;
- provisional automatic ion-selection rules.

Future ions require an evidence-aware state-selection design, especially for
anions and heavy elements. They should be introduced as explicitly identified
datasets rather than guessed through scalar transfer policies.

Additional scalar or radial properties should continue to use the same registry
and `get_builtin_set()` machinery whenever their key space and payload can be
represented clearly.

### 16.2 Future three-dimensional grid-density generation

A future release may add functions that sample radial proatomic profiles onto a
three-dimensional grid.

Conceptual workflows:

```python
single = proatomic_density_grid(
    element,
    position,
    grid=...,
    ...
)

total = promolecular_density_grid(
    atoms,
    grid=...,
    ...
)
```

The exact API is intentionally unresolved.

Potential supported nonperiodic grid description:

- origin vector;
- integer shape `(nx, ny, nz)`;
- three grid-step vectors, allowing non-orthogonal grids;
- coordinate unit;
- density output unit;
- radial cutoff not exceeding the profile domain.

Potential periodic extension:

- periodic cell vectors;
- atomic Cartesian or fractional coordinates;
- explicit periodic axes;
- summation over every periodic image intersecting the radial cutoff;
- correct handling of skew cells and grids;
- no assumption that wrapping an atom once is equivalent to image summation.

Important design questions:

1. Should the API require NumPy through an optional extra?
2. Should it accept/output an array protocol rather than nested Python lists?
3. How should memory allocation and chunking work for large crystallographic
   grids?
4. Should the single-atom function be public if the multi-atom implementation
   needs a more efficient shared kernel?
5. How are cell, grid, and atomic coordinate units represented?
6. How are periodic images enumerated robustly for triclinic cells?
7. Is the 20-bohr radial cutoff always sufficient for the intended grid use?
8. Should atomic contributions be returned separately or only summed?
9. How are spin-resolved or ionic profiles represented later?

Recommended direction:

- stabilize and validate scalar radial evaluation and the two pairwise modes first;
- gather requirements from actual crystallographic grid formats;
- design nonperiodic and periodic behavior together;
- use an optional NumPy-based extra rather than making NumPy a core runtime
  dependency;
- implement one optimized multi-atom kernel and let any single-atom convenience
  wrapper call the same core where efficient;
- add independent tests against direct pointwise profile sums.

This is a plausible and valuable `atomref` capability because it converts the
package’s reference radial functions into spatial promolecular densities.
Nevertheless, premature implementation would risk choosing the wrong array,
periodicity, and grid conventions.

### 16.3 Other possible future work

Future candidates, only after demonstrated need:

- vectorized one-dimensional profile evaluation;
- user-supplied radial sets with the same interface;
- ionic profile datasets and state selectors;
- additional reference functions;
- direct helpers for stockholder initialization;
- optional integration utilities for common crystallographic grid formats.

Do not turn this list into active tasks during `0.2.0` or `0.2.1`.

## 17. Suggested commit sequence

Preferred linear history for `0.2.0`:

```text
refactor: generalize built-in dataset loading
feat(data): add neutral proatomic density snapshot
feat: add proatomic density evaluation
feat: add two-mode proatomic IAS position estimates
docs: add IAS method study and proatomic density feature notebook
chore: prepare atomref 0.2.0
```

Preferred linear history for `0.2.1`:

```text
docs: make notebooks executable documentation
docs: complete typed API reference
docs: reposition atomref documentation
chore: prepare atomref 0.2.1
```

Commits may be combined when changes are inseparable, but do not combine an
entire release into one opaque commit.

Do not rewrite accepted history.

## 18. Agent completion report template

Use this template after each stage:

```text
Stage:
  <number and title>

Implemented:
  - ...

Files added:
  - ...

Files removed:
  - ...

Files changed:
  - ...

Validation:
  - <command>: <result>

Plan deviations:
  - none
  or
  - proposed design:
  - issue found:
  - replacement:
  - justification:
  - protecting tests:

Open questions:
  - ...

Suggested commit:
  <conventional commit message>

Next step:
  <one concise next action>
```

## 19. Open review points for this draft

Review before the corresponding implementation stage:

1. Final atomref-side density dataset ID.
2. Final radial loaded-set class name:
   - `ElementRadialSet`;
   - or `ProatomicDensitySet`.
3. Exact generic `get_builtin_set()` return annotation and scalar narrowing
   helper names.
4. Final public spelling of the three pairwise functions and result type.
5. Final status and method vocabulary, without changing their required
   distinctions.
6. Whether `IAS_MINIMUM_RESOLUTION_BOHR` and the practical competitive-depth
   threshold should be public constants or provenance-only fields.
7. Whether the minimum result should expose one explicit runner-up object or
   flattened optional fields.
8. Whether the supporting notebook remains a permanent documentation artifact
   after `0.2.1` adopts direct notebook rendering.
9. Final `0.2.1` notebook renderer and normalization details.
10. Final MkDocs/mkdocstrings visual settings after a local rendered preview.
11. The future grid-density requirements once actual target formats are
    collected.
12. A future curated molecular-QTAIM benchmark for comparing midpoint,
    equal-contribution, and promolecular-minimum coordinates.

These are review points, not permission to change the fixed cutoff, default
mode, homonuclear midpoint, explicit mode separation, provenance, range,
dataset-unification, unit, or compatibility contracts.

## 20. Plan closeout and replanning record

This section is intentionally left as a template while the plan is `ACTIVE`.
The implementation agent MUST complete the appropriate subsection before
changing the lifecycle state to `COMPLETE_AWAITING_REVIEW` or
`REPLAN_REQUIRED`.

### 20.1 Completion record

```text
Lifecycle state:
  COMPLETE_AWAITING_REVIEW

Completed releases/stages:
  - ...

Final commits or pull requests:
  - ...

Acceptance checks:
  - <command>: <result>

Binding requirements not implemented:
  - none
  or
  - <requirement and explicit owner-approved reason>

Plan deviations:
  - none
  or
  - <deviation, reason, and protecting tests>

Future-reference items intentionally not touched:
  - ...

Known limitations remaining within the accepted release:
  - ...

Implementation agent conclusion:
  - <why the plan is believed complete>

External review required:
  - verify repository diff and history
  - verify acceptance checklist
  - verify scientific and unit contracts
  - verify documentation and packaged artifacts
  - either set state to CLOSED or return the plan to ACTIVE with corrections
```

### 20.2 Replanning-required record

```text
Lifecycle state:
  REPLAN_REQUIRED

Blocked stage:
  - ...

Observed problem:
  - ...

Why the current plan cannot safely continue:
  - ...

Evidence and reproduction:
  - ...

Approaches attempted:
  - ...

Partial changes present:
  - ...

Repository/branch safety state:
  - clean / partial changes retained / revert recommended / other

Decisions requiring a new plan:
  - ...

Suggested replanning questions:
  - ...

Implementation agent conclusion:
  - stop implementation and request external review/replanning
```

### 20.3 External reviewer disposition

```text
Reviewer:
  - ...

Review date:
  - ...

Disposition:
  - CLOSED — completed
  - CLOSED — superseded/abandoned
  - ACTIVE — corrections required under this plan
  - REPLAN_REQUIRED — a replacement plan must be prepared

Review notes:
  - ...
```
