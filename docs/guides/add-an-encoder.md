# Add an encoder

For a new encoder that reads an existing family. Encoder folders live in `perception/encoders/` and are built into images; they are not part of the installed package.

## Before you start

- The encoder reads one existing family. Its code, weights and test data have licenses that allow you to package them.
- Test data for the family: synthetic or openly licensed, with a provenance note.

## Steps

1. Create the encoder folder:

    ```bash
    medomni perception new <family>/<encoder>
    ```

    It writes:

    ```text
    perception/encoders/<family>/<encoder>/
    ├── adapter.py
    ├── card.yaml
    ├── Dockerfile
    ├── assets.json
    └── testdata/       empty, filled in step 4
    ```

2. Implement the adapter and pin the image:
    - `encode(sample, options)` in `adapter.py`, with expensive set-up in `load()`
    - base image, dependencies and source revision pinned in the Dockerfile
    - torch, if the encoder needs it, installed with `torch==<version>` from the CPU build index, at a version listed in `src/medomni/perception/registry/torch.yaml`
    - weights and other files in `assets.json`, each with its source (a URL or a Hugging Face file) and sha256; the image build fetches and checks them
3. Write the model card: the family, outputs, options, license and source. See [Encoders](../reference/encoders.md).
4. Write the test data, its inputs and `PROVENANCE.md`:

    ```bash
    medomni studio testdata <family>__<encoder>
    ```

5. Record the expected responses on the test data, and open a pull request.

    ```bash
    medomni perception check perception/encoders/<family>/<encoder> --freeze
    ```

## Check

```bash
medomni perception check perception/encoders/<family>/<encoder>
```

It validates the model card with `medomni contracts check`, checks the Dockerfile's torch installs against the list, builds the image, checks the torch inside it is a listed CPU build, and runs the encoder's tests: it runs the image on the test data and compares the responses with `expected.json`. See [Check and freeze](../learn/perception/encoders.md#check-and-freeze). GPU encoders may run on a self-hosted runner.

Submit it as a pull request, or ship it in your own plug-in package. [Contribute](contribute.md) covers both.

## Where next

- [Contribute](contribute.md): pull requests, plug-in packages and how MedOmni is developed.
- [Encoders](../learn/perception/encoders.md): how an encoder is checked, recorded and served.
- [Encoders reference](../reference/encoders.md): the model card fields.
