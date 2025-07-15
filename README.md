# CreatistBackend

This is the backend for the Creatist project, built with FastAPI and integrated with Supabase and PostgreSQL.

## Features
- User authentication with JWT
- OTP email verification
- Supabase integration
- PostgreSQL database support
- Email notifications

## Requirements
- Python 3.11+
- PostgreSQL database (Supabase or local)

## Setup
1. **Clone the repository:**
   ```sh
   git clone https://github.com/anishumar/CreatistBackend.git
   cd CreatistBackend
   ```
2. **Create and activate a virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Create a `.env` file:**
   Copy the following into a `.env` file in the project root and fill in your secrets:
   ```env
   HOST="0.0.0.0"
   PORT="8080"
   JWT_SECRET="YOUR_SECRET"
   SUPABASE_URL="YOUR_SUPABASE_URL"
   SUPABASE_KEY="YOUR_SUPABASE_KEY"
   EMAIL_ADDRESS="your@email.com"
   EMAIL_PASSWORD="your_email_password"
   EMAIL_HOST="smtp.gmail.com"
   EMAIL_PORT="587"
   EMAIL_FROM="Your Name <your@email.com>"
   DATABASE_URL="postgresql://user:password@host:port/dbname?sslmode=require"
   ```

## Running the App
```sh
python main.py
```

Or use the provided `run.sh` script:
```sh
./run.sh
```

## Testing
```sh
pytest
```

## Project Structure
- `src/` - Main application code
- `src/routes/` - API route definitions
- `src/models/` - Database models and enums
- `src/utils/` - Utility functions (email, logging, etc.)
- `static/` - Static files (e.g., email templates)
- `tests/` - Test cases

## License
MIT 