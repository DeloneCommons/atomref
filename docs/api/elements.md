# atomref.elements

Element identity is intentionally minimal: atomic number, symbol, and name.
The module also contains the canonicalization helpers used throughout the
package.

::: atomref.elements
    options:
      members:
        - Element
        - canonicalize_element_symbol
        - is_valid_element_symbol
        - get_element
        - iter_elements
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
