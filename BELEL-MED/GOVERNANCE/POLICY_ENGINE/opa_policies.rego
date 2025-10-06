package belel.policies

default allow := false

# Example: prohibit autonomous medication ordering
allow {
  input.action == "draft_order_set"
  input.requires_signoff == true
}

deny[msg] {
  input.action == "place_medication_order"
  msg := "Autonomous ordering not permitted"
}
