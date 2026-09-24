# Verification (2026-09-24)

Semantic smoke test (encoder-semantics.md §3), dev image, 50 APTOS-2019 images from the RETFound BENCHMARK.md test split (10 per grade; held out from fine-tuning; not redistributed):

| truth \ predicted | none | mild | moderate | severe | proliferative |
|---|---|---|---|---|---|
| none | 10 | 0 | 0 | 0 | 0 |
| mild | 0 | 4 | 6 | 0 | 0 |
| moderate | 0 | 0 | 10 | 0 | 0 |
| severe | 0 | 0 | 5 | 3 | 2 |
| proliferative | 0 | 0 | 3 | 1 | 6 |

Exact grade 33/50; referable DR (moderate or worse, dr_referable > 0.5) agrees on 44/50. Errors fall on adjacent grades only, so the head's class order (folders anodr < bmilddr < cmoderatedr < dseveredr < eproliferativedr) is wired correctly.
The fixture's normal eye (`input.dcm`) is graded dr_none. Smoke tests do not establish clinical reliability on this cohort's devices.
