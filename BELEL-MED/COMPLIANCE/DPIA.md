# Data Protection Impact Assessment (DPIA)

**System:** BELEL-MED  
**Purpose:** Clinical decision support and patient triage/longitudinal coaching.  
**Lawful bases:** Healthcare provision; vital interests; explicit consent where applicable.

## Data Flows
- Sources: EHR (FHIR), imaging (DICOM), labs, pharmacy, devices, wearables.
- Storage: Encrypted at rest; segregated PHI; audit logging.
- Processing: Evidence-locked inference; role-based access; privacy-preserving learning.

## Risks & Mitigations
- Re-identification: de-identification, DP noise, access controls.
- Misuse: policy engine fences, human-in-loop, tiered evidence thresholds.
- Bias: calibration by subgroup; continuous monitoring; fairness reports.

## Residual Risk
Medium → reduced to Low with governance + monitoring.
