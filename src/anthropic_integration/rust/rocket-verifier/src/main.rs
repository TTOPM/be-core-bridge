#[macro_use] extern crate rocket;
use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};

#[derive(Deserialize)]
struct ProofData {
    input: String,
    prompt: String,
    output: String,
    timestamp: u64,
    protocol: String
}

#[derive(Deserialize)]
struct VerifyBody {
    proof_hash: String,
    proof_data: ProofData
}

#[derive(Serialize)]
struct VerifyResp {
    ok: bool,
    recomputed: String
}

#[post("/verify", format = "json", data = "<body>")]
fn verify(body: rocket::serde::json::Json<VerifyBody>) -> rocket::serde::json::Json<VerifyResp> {
    let mut hasher = Sha256::new();
    let data = serde_json::to_string(&body.proof_data).unwrap();
    hasher.update(data.as_bytes());
    let recomputed = format!("{:x}", hasher.finalize());
    rocket::serde::json::Json(VerifyResp {
        ok: recomputed == body.proof_hash,
        recomputed
    })
}

#[launch]
fn rocket() -> _ {
    rocket::build().mount("/", routes![verify])
}
