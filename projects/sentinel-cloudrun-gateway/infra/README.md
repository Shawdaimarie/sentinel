# SENTINEL four-cloud staging package

Status: configuration preparation. No provider account has been connected, no cloud plan has been applied, and no cloud deployment has been verified. Templates target existing, verified account/network/database foundations. They do not silently create billing accounts, paid databases, clusters, public load balancers, or identities for arbitrary users.

| Target | Workload | Identity | Foundation required |
|---|---|---|---|
| Google Cloud (first staging target) | Cloud Run, bundled explorer/API | Direct IAP; application verifies signed IAP assertion and maps exact allowed identities | Project/billing/APIs, private VPC/subnet and managed PostgreSQL, versioned Secret Manager values, image registry, IAP OAuth setup |
| AWS | ECS Fargate service on private subnets, existing private target group | Application OIDC; separate task execution/runtime roles; Secrets Manager | Account/region, ECS cluster, private subnets/security groups, private TLS load balancer/target group, private RDS, ECR, OIDC issuer |
| Microsoft Azure | Internal Container App | Application OIDC; user-assigned managed identity; Key Vault references | Subscription/resource group, private Container Apps environment, PostgreSQL, dedicated Key Vault, ACR, OIDC issuer |
| Oracle Cloud | Deployment and ClusterIP service on existing private OKE | Application OIDC; OCI Vault CSI synchronization; no automatic service-account API token | Tenancy/compartment, OKE/kubeconfig, namespace/network policy, private PostgreSQL, OCIR pull secret, OCI Vault CSI driver/provider and SecretProviderClass, OIDC issuer |

Oracle uses the official Kubernetes provider to configure the OKE workload. This package does not provision an OKE cluster. Azure/Oracle artifact-store integration and all four managed-database foundations remain explicit account-specific prerequisites. Google and AWS create private evidence buckets, but bucket creation alone does not prove application artifact upload works.

## Safe validation
Run `sh infra/validate.sh` from the repository. Docker runs Terraform 1.13.5 by digest; each module pins its provider and includes a lockfile. Tests use mock providers and synthetic resource identifiers, never cloud credentials. They verify structure and configured guardrails, not the existence or security of real infrastructure. AWS IAM document data is mocked to valid JSON during these tests, so this does not independently verify the semantic correctness of its final IAM policies.

## Configuration contract
All templates force `SENTINEL_ENVIRONMENT=staging`, clear local fixture tokens, and require an immutable `@sha256:` image. GCP forces `SENTINEL_AUTH_MODE=iap` and constructs the Cloud Run IAP audience from project number, region and service name. The other three force `SENTINEL_AUTH_MODE=oidc`.

Provide non-secret identity configuration in `runtime_environment`:
- GCP: `SENTINEL_IAP_IDENTITIES`, JSON mapping reviewed email identities to distinct requester/admin actors and tenant IDs. The `iap_members` list must agree with this mapping.
- Others: `SENTINEL_OIDC_ISSUER`, `SENTINEL_OIDC_JWKS_URL`, `SENTINEL_OIDC_AUDIENCE`, `SENTINEL_OIDC_IDENTITIES` (exact issuer subjects mapped to tenant/role). Generic OIDC browser login/session integration must be verified with the chosen provider; a working bearer API does not prove browser sign-in.
- `DATABASE_URL` and `CAPABILITY_SECRET` are injected through cloud secret references, never supplied as plaintext Terraform variables. Do not put these keys in `runtime_environment`.
- Build the bundled gateway image with the same-origin explorer (`VITE_SENTINEL_API_BASE` empty); do not deploy the local bearer identity-selector build as a production login interface.

Copy a module's `terraform.tfvars.example` to its ignored `terraform.tfvars` and replace every synthetic identifier. Examples are deliberately not deployable. Use TLS-verified database connections and a runtime DB role with no schema ownership; execute versioned migrations with a separate migration identity. No runtime synthetic seeding is acceptable outside local mode.

## GCP direct IAP details
Direct IAP is enabled on Cloud Run. Internet-reachable HTTPS ingress is identity-protected, not anonymous. Only the IAP service agent receives Cloud Run invoker access; approved users receive IAP resource access. The application independently validates assertions. This must be tested on the actual project, including bypass attempts. A project without an organization may require interactive OAuth client setup first; Terraform cannot create that client programmatically in that situation. Do not disable IAP to work around setup failures.

## Account setup and deployment sequence
1. Choose verified account/project/subscription/tenancy IDs, region, two distinct test users, identity issuer and an explicit infrastructure budget. Sign in through each provider's own console/CLI; never put credentials in chat or source.
2. Establish restricted state storage with locking/encryption and access logs. Local state is suitable only for the no-account mock tests. Configure the remote backend before a real apply; preserve state securely.
3. Verify foundation resources, required APIs, private routes, DNS, outbound JWKS access, secret versions, database roles/backups, registry access, and ingress protections. AWS task subnets need appropriate private endpoints or NAT for ECR/logs/Secrets Manager and trusted JWKS. OCI requires a namespace default-deny policy plus explicit ingress/DB/DNS/JWKS allowances before running the workload.
4. Run all release checks, resolve failures, bind evidence to the tested source revision, build once and record/push the reviewed image digest to the chosen registry. Each cloud must receive the same tested source build for portability comparisons.
5. In the selected module run `terraform init` with the approved backend, `terraform plan -out=staging.tfplan`, and review costs, identities, secret references and networking. The first target is GCP. Only an approved account-specific plan and release gate can proceed to `terraform apply staging.tfplan`.
6. Run authenticated staging acceptance: requester/approver separation, cross-tenant denial, expiry/replay/tampering, transaction failure, schema/version checks, concurrency, browser flow, artifact upload, managed DB backup/restore, image rollback, declared-load and cost checks.
7. Record actual service URI, cloud revision/image digest, source commit, commands, raw evidence and remaining gaps. Repeat independently for each additional provider. Do not infer AWS/Azure/OCI success from GCP success.

## Recovery and rollback
GCP: retain prior image digest/revision and compatible schema; route back only after compatibility check. AWS: deployment circuit breaker rolls back failed service deployment, but database changes need independent recovery. Azure: retain previous revision/config and restore known-good image if the new revision fails. OKE: retain Deployment revision and use rollout rollback only with compatible schema. Exercise managed DB restore in a separate instance and compare records/audit chains; never overwrite the primary database as a first test.

## Remaining account inputs
No GCP/AWS/Azure/OCI CLI or account configuration was present when inspected. Needed: account identifiers/access, selected identity provider and users, network/database/secret resource IDs, image registry, remote state and cost limits. Authorization to configure clouds does not supply these values. The templates remain un-applied until these prerequisites and release evidence exist.

## Primary references
- GCP direct IAP: https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run
- GCP Direct VPC: https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc
- AWS ECS secrets: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data.html
- Azure managed secret references: https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets
- OCI OKE secrets: https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengmanagingsecrets.htm

References checked 2026-11-02. These explain supported mechanisms, not SENTINEL's deployed compliance.
