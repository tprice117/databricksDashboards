import {
  to = segment_destination.id-653dab7b197c4072a12619c5
  id = "653dab7b197c4072a12619c5"
}

resource "segment_destination" "id-653dab7b197c4072a12619c5" {
  enabled = true
  metadata = {
    contacts          = null
    id                = "61957755c4d820be968457de"
    partner_owned     = false
    region_endpoints  = ["US"]
    supported_regions = ["us-west-2", "eu-west-1"]
  }
  name      = "Salesforce PRD"
  settings  = "{\"isSandbox\":false}"
  source_id = "uQMpUymuMWo75mypkjJoqH"
}