#!/usr/bin/env python
"""Generate an SWMF input file from interval-averaged MMS observations.

Examples
--------
Generate the SWMF input and save the MMS quick-look plot::

    ./tools/create_swmf_input.py \
        --mms-start "2018-12-19 19:40:00" \
        --mms-end "2018-12-19 19:52:00" \
        --plot

The plot is saved as
``mms_20181219_194000_20181219_195200.png`` beside the SWMF input.
"""

from shocklink.mms_swmf import main


if __name__ == "__main__":
    raise SystemExit(main())
