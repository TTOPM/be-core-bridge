package belellex.policies

default allow := false

# Drafts only; never auto-file
allow {
  input.action == "draft_document"
  input.requires_signoff == true
}

deny[msg] {
  input.action == "submit_to_court"
  msg := "Autonomous filing prohibited"
}
