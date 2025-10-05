FROM rust:1.80 as builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:stable-slim
WORKDIR /app
COPY --from=builder /app/target/release/rocket-verifier /usr/local/bin/rocket-verifier
EXPOSE 8001
CMD ["rocket-verifier"]
