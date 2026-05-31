# Server runtime package

This archive is for running the FastAPI backend on the Ubuntu 22.04 GPU server while the frontend can remain on the local development computer.

Included:
- server/ backend code
- tools/ helper scripts
- backend smoke-test files
- deployment planning docs
- selected project docs

Excluded:
- NIfTI/CT data (*.nii, *.nii.gz)
- model checkpoints (*.pth, *.pt)
- node_modules/
- dist/
- server/work/
- logs
- .env files

Expected server-side setup:
1. Install Python dependencies, CUDA, PyTorch, nnUNetv2, FastAPI and uvicorn in the server environment.
2. Configure SEGMENTATION_ALLOWED_ORIGINS and SEGMENTATION_SERVER_* environment variables.
3. Run from the extracted project root:
   python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
