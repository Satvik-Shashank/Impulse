# Contributing Guidelines

Thank you for contributing to the Chargeback Intelligence Platform!

## Local Setup
1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd Razorpay
   ```
2. Activate virtual environment:
   ```bash
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Development Workflow
1. Run tests before submitting changes:
   ```bash
   .venv\Scripts\pytest
   ```
2. Generate synthetic data & evaluate:
   ```bash
   .venv\Scripts\python -m src.data.generate_disputes
   .venv\Scripts\python -m src.evaluate
   ```
3. Keep documentation updated under `docs/` and log major decisions in `PROJECT_STATUS.md`.
