# NIH/NSF At-Risk Labs Tracker

A full-stack web application that identifies early warning signs of lab job losses based on terminated NIH/NSF grants, similar to layoffs.fyi but for research grants.

## Features

- **Risk Scoring Algorithm**: Calculates risk scores for institutions based on terminated grants
- **Institution Leaderboard**: Shows institutions ranked by risk score
- **Real-time Data**: Fetches data from NIH RePORTER API
- **Modern UI**: Clean, responsive interface

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React with TypeScript
- **API**: NIH RePORTER API

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the FastAPI server:
   ```bash
   python main.py
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

The frontend will be available at `http://localhost:3000`

## API Endpoints

- `GET /`: Root endpoint
- `GET /api/risk-leaderboard`: Get institution risk leaderboard
- `GET /api/health`: Health check endpoint

## Risk Scoring Algorithm

The risk score is calculated as:
```
risk_score = (terminated_grants * 3) + (non_renewed * 2) + (funding_drop / 500000)
```

Currently, `non_renewed` and `funding_drop` are set to 0, so the formula simplifies to:
```
risk_score = terminated_grants * 3
```

## Data Source

Data is sourced from the NIH RePORTER API:
- **Endpoint**: `https://api.reporter.nih.gov/v2/projects/search`
- **Time Range**: Last 12 months of terminated grants
- **Update Frequency**: Real-time API calls

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.
