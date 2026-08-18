# Test certificates

Local CA and a server certificate for `httpbin.local`, used only by the local
benchmark stand. Nothing here is a real secret, but generated keys are still
kept out of git.

Generate everything:

```bash
bash certs/generate.sh
```

Inspect:

```bash
openssl x509 -in certs/httpbin.local.crt -text -noout
openssl verify -CAfile certs/ca.crt certs/httpbin.local.crt
```
