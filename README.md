# model-deploy

## Documentation

- [MD.ai Interface Code](https://docs.md.ai/models/interface-code/)
- [Deploying Models](https://docs.md.ai/models/deploy-models/)
- [Inference](https://docs.md.ai/models/inference/)
- ...more to come, including training and validation

## Examples

Example model deployments for training/validation/inference on MD.ai are located in the `examples/` folder.

## Development [MD.ai Internal Only]

### Setup

Python 3.7+ required. Initial setup:

```sh
# Create virtualenv
virtualenv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt
```

### File Structure

The file structure below needs to be followed. Create a root folder named `model`. Inside this folder, store your pre-trained model file. Along with this, create a subfolder named `.mdai` and all the MD.ai related build files need to be placed inside this folder.

```sh
model/
  |__ .mdai/
      |__ config.yml            # Contains configuration parameters to be used during build
      |__ mdai_deploy.py        # Framework which communicates between server and model
      |__ requirements.txt      # Lists the libraries needed to run the model
  |__ model_file.pth            # Pretrained model checkpoint file
```

The uploaded model assets file should be a compressed file: accepted formats are `.zip` and `.tar.gz`. To compress the model folder, use the following command:

```sh
# compress to .zip
zip -r model.zip /path/to/model
```

or

```sh
# compress to .tar.gz
tar -czvf model.tar.gz /path/to/model
```

### Building the image

To build a production image, we use the `dev/build-image.py` script

```sh
dev/build-image.py --image_name <image_name> --target_folder <path_to_root_folder>
```

To build an image for dev usage,`--hot_reload` arg is used. This auto-refreshes the server which saves significant time in building and running the image again. An example is as follows

```sh
dev/build-image.py --image_name <image_name> --target_folder <path_to_root_folder> --hot-reload
```

### Running the image

In order to run the built image, we use the `dev/run-image.py` script. This runs the most recently built image.

```sh
dev/run-image.py
```

### Testing the image

The output from the container can be tested using the `dev/inference.py` script. This sends images to the deployed model to be tested and receives results as JSON.

```sh
dev/inference.py <path_to_test_data>
```

### Usage statistics

To profile memory usage of the container, the `dev/profile.py` script can be used.

```sh
dev/profile.py
```

## Pinned Libraries and Known/Tracking Issues

Do not upgrade the following libraries for now:

- `protobuf@3.20.1` in [mdai/requirements.txt](mdai/requirements.txt) (latest protobuf versions break older TF models, see [#10051](https://github.com/protocolbuffers/protobuf/issues/10051))
- `requests<2.29.0` in [requirements.txt](requirements.txt) (latest urllib3 versions breaks docker build, see [#3113](https://github.com/docker/docker-py/issues/3113))

---

&copy; 2023 MD.ai, Inc.
