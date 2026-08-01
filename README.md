# Assessly AI Hiring Agent

> An AI-powered hiring workflow that transforms job requirements into validated hiring decisions.

![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?logo=snowflake&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Cortex AI](https://img.shields.io/badge/Cortex_AI-mistral--large2-purple)

## Features

- **AI Competency Mapping** — Analyzes job requirements and maps competencies automatically
- **Assessment Generation** — AI generates tailored assessments (MCQ, Short Answer, Essay)
- **Candidate Portal** — Candidates take assessments directly in the application
- **AI Evaluation** — Automated scoring with detailed feedback
- **Hiring Recommendations** — Data-driven recommendations with explainable reasoning

## Architecture

```
Recruiter → Describe Job → AI Agent → Competency Map → Generate Questions
                                                              ↓
Hiring Report ← AI Evaluation ← Submit Answers ← Candidate Portal
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit in Snowflake |
| AI Model | Snowflake Cortex AI (mistral-large2) |
| Database | Snowflake |
| Backend | Stored Procedures (JavaScript) |

## Setup

### 1. Run Database Setup

Execute `scripts/setup_database.sql` in a Snowflake worksheet.

### 2. Deploy Streamlit

```sql
CREATE STAGE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE;

PUT file://streamlit/assessly_app.py @ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE/ OVERWRITE=TRUE AUTO_COMPRESS=FALSE;
PUT file://streamlit/environment.yml @ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE/ OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

CREATE OR REPLACE STREAMLIT ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSLY_APP
    ROOT_LOCATION = '@ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE'
    MAIN_FILE = '/assessly_app.py'
    QUERY_WAREHOUSE = 'COMPUTE_WH'
    TITLE = 'Assessly - AI Hiring Agent';
```

### 3. Access

Snowsight > Projects > Streamlit > ASSESSLY_APP

## Project Structure

```
assessly-ai-hiring-agent/
├── README.md
├── scripts/
│   └── setup_database.sql
└── streamlit/
    ├── assessly_app.py
    └── environment.yml
```

## License

MIT
