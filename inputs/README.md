# inputs/

Store YAML input files for Boltz-2 runs here. Organize by project or dataset:

```
inputs/
  my_project/
    20260131T120000_run1.yaml
    20260201T090000_run2.yaml
```

Guidelines:
- Small parameter YAMLs that reproduce runs may be committed to git.
- Avoid storing secrets (API keys). Use `.env` for API keys.
- Use descriptive filenames with timestamps.
