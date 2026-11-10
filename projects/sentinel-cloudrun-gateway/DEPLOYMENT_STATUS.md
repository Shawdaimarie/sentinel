# Deployment status

## Current state

The Cloud Run release package and local application are prepared, but no Google Cloud resources have been created and no spend has been incurred or authorized. The existing VECTOR project remains untouched. The documented deployment target is a new, dedicated SENTINEL project.

Completed locally: signed IAP and generic OIDC verification contracts, production-mode fail-closed checks, identity/role separation enforcement, least-privilege runtime database grants, versioned migration, same-origin explorer packaging, Cloud Run Terraform modules and no-apply validation workflow. See [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md) and `infra/README.md` for the operator contract and deployment package.

## Outstanding inputs and gates

The current authorization is a $0.00 spend cap, and only one Google identity (`shawdaimarie@gmail.com`) has been supplied. Deployment requires:

1. A new dedicated Google Cloud project name/ID. It must be separate from VECTOR.
2. An explicit maximum staging spend above $0.00 (or continued pause on deployment).
3. A second distinct Google identity for the approver. Owner and approver accounts and actor IDs must be distinct.
4. Google Cloud access for the chosen project and approved billing setup. No credentials or `gcloud` installation were available to this workstation during this run.

The design target of $50/month is not authorization. The configured hard limit must be supplied by the project owner. Until the outstanding items are settled, do not run Terraform apply, create cloud resources, enable billing, or claim Cloud Run end-to-end verification.

## What local verification does and does not establish

The isolated Docker Compose suite verifies application behavior, auth token validation, local database permissions, rollback, backup/restore mechanics, and declared local route load. It does not prove Cloud Run identity propagation, Cloud SQL connectivity/restore, deployed tenant isolation, cloud cost, cloud autoscaling, or hosted rollback. Those require a staging project and independent verification after authorization.
