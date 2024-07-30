import {
  to = segment_source.id-uQMpUymuMWo75mypkjJoqH
  id = "uQMpUymuMWo75mypkjJoqH"
}

resource "segment_source" "id-uQMpUymuMWo75mypkjJoqH" {
  enabled = true
  labels  = null
  metadata = {
    id = "WvlvcGEJsT"
  }
  name     = "Postgres"
  settings = "{\"database\":\"defaultdb\",\"hostname\":\"db-postgresql-nyc1-05939-do-user-13480306-0.b.db.ondigitalocean.com\",\"port\":\"25060\",\"username\":\"doadmin\"}"
  slug     = "postgres"
}