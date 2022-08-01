# AutoML Edge (Vertex AI) classification models

AutoML Edge models trained using Google Cloud's Vertex AI offering can now be easily deployed on MD.ai. The following steps outline the process for deploying image classification models -

- Export your model as a TF Saved Model by following steps for the `Container` format mentioned [here](https://cloud.google.com/vertex-ai/docs/export/export-edge-model#aiplatform_export_model_sample-console). This will download a `saved_model.pb` file to the Google cloud storage bucket of your choice.
- Download this `saved_model.pb` file from your bucket.
- Download the sample code for deploying AutoML edge models on MD.ai from here - [vertex-ai-mdai-template.zip](https://mdai-assets.s3.amazonaws.com/github/mdai/model-deploy/vertex_ai_template.zip)
- For binary and multiclass models, you simply need to replace the `saved_model.pb` file in this sample zip file with your own exported model file.
- Optionally, in the `.mdai/config.yaml` file change the `device_type` to `gpu` if required to run inference on a GPU.
- For multilabel or more complex models, make changes in the `.mdai/mdai-deploy.py` file as required depending on your model definition.
- Finally, follow our [documentation](https://docs.md.ai/models/deploy-models/) for steps to deploy models into a project.

More details can be found in our [documentation](https://docs.md.ai/models/vertex-ai-integration).
