# Infrastructure for meta-science.
#
# Two services, both load-bearing rather than decorative: Firestore is the ledger the
# promotion gate writes its receipts to, and Cloud Run is where a discovery run
# executes. Neither is present to satisfy a checklist — remove either and the system
# stops doing what it claims.

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "GCP project hosting the ledger and the run service."
}

variable "region" {
  type        = string
  default     = "europe-west1"
  description = "Cloud Run region. EU by default — the operator is EU-resident."
}

variable "firestore_location" {
  type        = string
  default     = "eur3"
  description = "Firestore multi-region. Fixed at creation and cannot be changed later."
}

variable "gemini_api_key" {
  type        = string
  sensitive   = true
  description = "Passed to Secret Manager, never baked into the image."
}

locals {
  service_name = "metascience"
  apis = [
    "firestore.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.apis)
  service  = each.value

  # The APIs outlive any single terraform destroy: disabling them would break anything
  # else in the project that came to depend on them.
  disable_on_destroy = false
}

# -- Ledger -------------------------------------------------------------------

resource "google_firestore_database" "ledger" {
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  # Deleting the database would destroy every promotion receipt, which is the audit
  # trail the whole governance claim rests on.
  deletion_policy = "ABANDON"

  depends_on = [google_project_service.required]
}

# -- Identity -----------------------------------------------------------------

resource "google_service_account" "runner" {
  account_id   = "${local.service_name}-runner"
  display_name = "meta-science Cloud Run service identity"
  description  = "Least privilege: writes ledger records and reads its own API key."
}

resource "google_project_iam_member" "runner_firestore" {
  project = var.project_id
  role    = "roles/datastore.user" # Firestore-native access; not an admin role.
  member  = "serviceAccount:${google_service_account.runner.email}"
}

# -- Secret -------------------------------------------------------------------

resource "google_secret_manager_secret" "gemini_key" {
  secret_id = "${local.service_name}-gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "gemini_key" {
  secret      = google_secret_manager_secret.gemini_key.id
  secret_data = var.gemini_api_key
}

resource "google_secret_manager_secret_iam_member" "runner_reads_key" {
  secret_id = google_secret_manager_secret.gemini_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runner.email}"
}

# -- Run service --------------------------------------------------------------

resource "google_cloud_run_v2_service" "app" {
  name     = local.service_name
  location = var.region

  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.runner.email

    # A discovery run is bursty and short. One request per instance keeps a run's
    # CPU to itself, so timings in the demo mean something.
    max_instance_request_concurrency = 1

    scaling {
      min_instance_count = 0 # scale to zero: this is demonstrated, not trafficked
      max_instance_count = 4
    }

    containers {
      image = var.image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "GEMINI_PROJECT"
        value = var.project_id
      }

      env {
        # The complex-variable master switch is off by default so experiment history
        # stays real-domain. The service opts in for the INSPECTOR only — a human
        # asking for T7 by name is presentation; collect.py and the benchmark never
        # request an EXTRA template, which tests assert.
        name  = "METASCIENCE_COMPLEX"
        value = "1"
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_key.secret_id
            version = "latest"
          }
        }
      }
    }

    timeout = "900s" # a full generation across 24 held-out worlds is not a fast request
  }

  depends_on = [google_project_service.required]
}

variable "image" {
  type        = string
  description = "Container image URI built by Cloud Build."
}

# Public read: judges need to reach the demo without credentials.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = google_cloud_run_v2_service.app.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "service_url" {
  value       = google_cloud_run_v2_service.app.uri
  description = "The hosted URL the submission points at."
}

output "ledger_database" {
  value = google_firestore_database.ledger.name
}
