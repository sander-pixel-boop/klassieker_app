# Sporza Giro d'Italia App

This is a standalone Streamlit application for the Sporza Giro d'Italia fantasy cycling game. It allows users to build and optimize their teams using data and linear programming.

## Installation

1. Clone the repository.
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

This application connects to a database (Supabase) and uses secrets. You must set up a `.streamlit/secrets.toml` file in the root directory (this file is ignored by Git for security reasons).

Create `.streamlit/secrets.toml` and populate it with your credentials:

```toml
TABEL_NAAM = "your_table_name"
CRYPTO_SALT = "your_crypto_salt"

[connections.supabase]
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
```

## Running the App

To run the application locally:

```bash
streamlit run sporza_giro_app.py
```
