# assets/

`donor-harvest/` lands here after the one-time bootstrap:

```bash
python ../scripts/harvest_donor.py /path/to/donor.msapp --out donor-harvest
```

Commit the harvest so every future app request can be compiled with zero Studio work.
Re-harvest only if imports break after a Power Apps platform update, or when a
richer donor (more seed control types / new data source connections) is needed.
