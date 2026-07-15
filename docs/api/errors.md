# atomref.errors

`atomref` distinguishes missing scientific data from invalid configuration or
malformed packaged data. Ordinary lookup misses use `None` or a missing
[`LookupResult`][atomref.LookupResult]; catchable operational failures use the
exceptions below.

The exceptions are imported from `atomref.errors` and are deliberately not
re-exported from the top-level package.

::: atomref.errors
    options:
      members:
        - AtomrefError
        - DatasetError
        - MissingValueError
        - PolicyError
      filters:
        - "!^_[^_]"
        - "!^__post_init__$"
