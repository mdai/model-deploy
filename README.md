# model-deploy

## Examples

Example model deployments for training/testing/inference on MD.ai are located in the `examples/` folder.

## Development

Python 3.7+ required. Initial setup:

```sh
# Create virtualenv
virtualenv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt
for f in $(ls ./**/requirements.txt); do pip install -r $f; done
```

---

&copy; 2020 MD.ai, Inc.
