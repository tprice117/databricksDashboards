import {
  to = segment_source.id-ruFmzELTykGdvaW9oXh7Tq
  id = "ruFmzELTykGdvaW9oXh7Tq"
}

resource "segment_source" "id-ruFmzELTykGdvaW9oXh7Tq" {
  enabled = false
  labels = [
    {
      key   = "environment"
      value = "prod"
    },
  ]
  metadata = {
    id = "IqDTy1TpoU"
  }
  name     = "Downstream Web App PRD"
  settings = "{\"website_url\":\"https://app.trydownstream.io\"}"
  slug     = "downstream_web_app_prd"
}