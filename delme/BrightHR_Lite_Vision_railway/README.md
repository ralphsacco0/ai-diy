# HR Management System

This is a lightweight HR management application built with Node.js, Express, SQLite, and plain HTML/CSS/JS. It supports user authentication, employee directory, and leave management with a focus on simplicity and portability.

## Setup on macOS (Ventura+)

1. Install Node.js v18+ via Homebrew:
   ```bash
   brew install node@18
   ```

2. Clone the repository:
   ```bash
   git clone <repo-url>
   cd <project-directory>
   ```

3. Install dependencies:
   ```bash
   npm install
   ```

4. Start the server:
   ```bash
   npm start
   ```
   The application runs on http://localhost:3000 (or process.env.PORT if set).

5. For tests:
   ```bash
   npm test
   ```
   Tests use an in-memory database (NODE_ENV=test) for isolation.

6. Database:
   On first run, `./data.sqlite` is created automatically in the project root. An admin user is seeded with:
   - Email: admin@test.com
   - Password: Password123!
   All paths are relative for cross-platform portability (works on macOS, Windows, Linux).

## Usage

- Access the login page at http://localhost:3000/login.
- Use the seeded admin credentials to log in.
- The app uses session-based authentication and redirects unauthenticated users to /login.

## Environment

- **Port**: Defaults to 3000 (configurable via PORT env var).
- **Database**: SQLite file `./data.sqlite` in production; in-memory for tests.
- **Dependencies**: See package.json (Express, sqlite3, bcryptjs, express-session).

For development, all code uses async/await with try/catch for error handling. The setup is designed for local runs on macOS Ventura+ but is portable to other platforms without changes due to relative paths and cross-platform libraries.

## Testing

Run `npm test` to execute Node.js native tests. No additional test frameworks are required.

## Deployment Notes

This setup is for local development. For production, consider adding HTTPS and environment variables for secrets.