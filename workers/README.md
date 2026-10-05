# AI Worker Layer

## Prospect Worker v1

Model: ggml-org/Qwen3-1.7B-GGUF:Q4_K_M.
Runtime: llama.cpp OpenAI-compatible server.
The Hugging Face artifact is Apache-2.0; the Q4_K_M file is about 1.28 GB.

Scope: qualify public buyer/request evidence and match it to a closed offer list.
It does not send outreach, make payments, access credentials, or claim a sale.

Architecture: Radar -> Prospect Worker -> deterministic validation -> controller decision -> outreach/payment.
The main radar remains deterministic until live inference quality is validated.

Do not commit the model binary. Download/cache it at runtime.