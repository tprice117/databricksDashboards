import {
  to = segment_destination_subscription.id-64d1b96c7887ccda3542fe5b_a2crV6ms6uJde5FZteqqfE
  id = "64d1b96c7887ccda3542fe5b:a2crV6ms6uJde5FZteqqfE"
}

resource "segment_destination_subscription" "id-64d1b96c7887ccda3542fe5b_a2crV6ms6uJde5FZteqqfE" {
  action_id      = "sXZzg4LGsu5WVyx5imvkWL"
  destination_id = "64d1b96c7887ccda3542fe5b"
  enabled        = true
  model_id       = "79sGD3fRcxkj5YPgwoQqPv"
  name           = "Identify Contact"
  settings       = "{\"email\":{\"@path\":\"$.properties.email\"},\"external_id\":{\"@path\":\"$.properties.id\"},\"name\":{\"@template\":\"{{properties.first_name}} {{properties.last_name}}\"},\"phone\":{\"@path\":\"$.properties.phone\"},\"role\":\"user\",\"signed_up_at\":{\"@path\":\"$.properties.created_on\"}}"
  trigger        = "event = \"new\" or event = \"updated\""
}