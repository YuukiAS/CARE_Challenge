# Architecture figure ZIP import addendum

Read this together with `prompts/tasks/20260805_public_repo_hygiene_and_architecture_assets_controller.md`.

The user may provide one archive named:

```text
CARE_architecture_figures.zip
```

Look for it in:

```text
/users/a/e/aereinh/CARE_visual_inbox/CARE_architecture_figures.zip
docs/architecture/figures_inbox/CARE_architecture_figures.zip
```

If present:

1. inspect the archive listing before extraction;
2. reject absolute paths, `..`, symlinks, non-PNG payloads and unexpected filenames;
3. require exactly the expected architecture figure names or record the exact missing/extra names;
4. extract only into a temporary server-local directory;
5. verify every image with Pillow or an equivalent PNG parser;
6. copy verified files into `docs/architecture/figures/`;
7. compute SHA256, dimensions and file size;
8. update `VISUAL_SOURCES.json` with public GitHub blob/raw URLs after push;
9. keep the ZIP itself ignored and server-local; do not commit the ZIP.

This addendum does not authorize enabling the Agent-Flow request. Visual smoke and exact scheduled-task bindings remain required first.
