# Architecture

Publicly, v0.1 is radii-first.

Internally, the package is built around element-indexed scalar datasets plus a
small transfer layer. That keeps the public API simple while leaving a clean
path to later quantities such as X-H bond lengths.
