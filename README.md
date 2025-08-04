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

## Deployment

### Railway Deployment (Recommended)

1. **Fork/Clone this repository to your GitHub account**

2. **Sign up for Railway** at [railway.app](https://railway.app)

3. **Create a new project** and select "Deploy from GitHub repo"

4. **Connect your repository** and Railway will automatically detect it's a Python app

5. **Add Environment Variables** in Railway dashboard:
   - `HOST`: `0.0.0.0`
   - `PORT`: `8080` (Railway will override this)
   - `ENVIRONMENT`: `production`
   - `JWT_SECRET`: Your secret key
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `EMAIL_ADDRESS`: Your email address
   - `EMAIL_PASSWORD`: Your email app password
   - `EMAIL_HOST`: `smtp.gmail.com`
   - `EMAIL_PORT`: `587`
   - `EMAIL_FROM`: Your email display name

6. **Add PostgreSQL Database** (Railway provides this):
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set the `DATABASE_URL` environment variable

7. **Deploy**: Railway will automatically build and deploy your app

8. **Get your URL**: Railway will provide a URL like `https://your-app.railway.app`

### Alternative Deployments

#### Render
- Similar to Railway but with Render's interface
- Use the same environment variables
- Add build command: `pip install -r requirements.txt`
- Add start command: `uvicorn src.app:app --host 0.0.0.0 --port $PORT`

#### Fly.io
- Install `flyctl` CLI tool
- Run `fly launch` in your project directory
- Configure environment variables in `fly.toml`

## License
MIT 