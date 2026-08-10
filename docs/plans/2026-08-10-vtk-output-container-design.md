# VTK Output Container Design

**Goal:** Keep each converted VTM metadata file and all generated sidecars together inside one clearly named output directory.

## Interface and layout

For an input named `sample.dat`, the default output container will be `sample_vtk/` beside the input:

```text
sample_vtk/
├── sample.vtm
└── sample/
    └── generated VTK sidecar files
```

The optional second positional argument will name the output container directory rather than a `.vtm` file:

```bash
./tools/convert_dat_to_vtm.py sample.dat
./tools/convert_dat_to_vtm.py sample.dat custom_vtk
```

In both cases the metadata filename remains `sample.vtm`, derived from the input stem. PyVista will write its sidecar directory relative to that metadata file, so every generated artifact remains within the container.

## Safety and behavior

The converter will continue to pass the `pyvista.MultiBlock` directly to `save()` without normalization or other data changes. It will create the output container if necessary.

`--delete-input` will remove `sample.dat` only after `sample.vtm` has been saved successfully. Read, validation, directory-creation, or write failures will leave the input untouched.

## Testing and documentation

Tests will verify the default and explicit container layouts, ensure all generated paths are inside the container, preserve every Tecplot zone, and retain deletion failure safety. The executable help and README examples will describe the new directory argument and default `_vtk` naming.
