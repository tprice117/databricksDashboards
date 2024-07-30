import {
  to = segment_label.id-environment_prod
  id = "environment:prod"
}

resource "segment_label" "id-environment_prod" {
  description = null
  key         = "environment"
  value       = "prod"
}