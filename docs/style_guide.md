# Coding Style Guides for ci_edit

## Python Style Guide

The initial ci_edit code followed a style similar to the Chromium Python style
guide. Over time, the ci_edit style will migrate towards the Google Python style
guide which is much closer to PEP-8. Some of that style can be attained with
yapf. E.g.

$ yapf -i --style google ci.py

## Rust Style Guide

Use rustfmt, e.g.

$ cargo fmt
