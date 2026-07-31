# Conventional MMS notebook design

## Goal

Refine the MMS example into a guided, conventional Jupyter notebook while
keeping the committed file free of execution outputs.

## Layout

The notebook will have Markdown sections for overview, requirements, editable
parameters, data download, available-product inspection, summary statistics,
plotting, and troubleshooting. Each action is contained in a small code cell
so users can run and alter the workflow incrementally.

## Behavior

The existing public example API remains unchanged. The notebook will preserve
its repository-root-compatible import setup and the burst-first `auto` cadence
default. It will not embed downloaded data, figures, or execution counts.

## Verification

Tests will verify the conventional section headings, editable settings cell,
existing root-launch import setup, and absence of saved outputs.
