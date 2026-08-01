# Assessly AI Hiring Agent

> An AI-powered hiring workflow that transforms job requirements into validated hiring decisions.

![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?logo=snowflake&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Cortex AI](https://img.shields.io/badge/Cortex_AI-mistral--large2-purple)

## Features

- **AI Competency Mapping** — Automatically analyzes job requirements and maps required competencies
- **Assessment Generation** — AI generates tailored assessments (MCQ, Short Answer, Essay)
- **Candidate Portal** — Candidates take assessments directly in the application
- **AI Evaluation** — Automated scoring with detailed feedback per answer
- **Hiring Recommendations** — Data-driven recommendations with explainable reasoning

## Architecture

```
Recruiter → Describe Job → AI Agent → Assessment Blueprint → Generate Questions
                                                                    ↓
Hiring Recommendation ← AI Evaluation ← Candidate Answers ← Candidate Portal
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit in Snowflake |
| AI Model | Snowflake Cortex (mistral-large2) |
| Database | Snowflake |
| Backend | Snowflake Stored Procedures (JavaScript) |

## Setup

### 1. Run Database Setup

Execute `scripts/setup_database.sql` in a Snowflake worksheet to create:
- Database & Schema (`ASSESSLY_DB.ASSESSLY_SCHEMA`)
- 7 tables (jobs, competencies, assessments, questions, candidates, candidate_answers, evaluations)
- 5 stored procedures (AI-powered)
- 1 helper function

### 2. Deploy Streamlit App

```sql
-- Create stage and upload files
CREATE STAGE IF NOT EXISTS ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE;

PUT file://streamlit/assessly_app.py @ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE/ OVERWRITE=TRUE AUTO_COMPRESS=FALSE;
PUT file://streamlit/environment.yml @ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE/ OVERWRITE=TRUE AUTO_COMPRESS=FALSE;

-- Create Streamlit
CREATE OR REPLACE STREAMLIT ASSESSLY_DB.ASSESSLY_SCHEMA.ASSESSLY_APP
    ROOT_LOCATION = '@ASSESSLY_DB.ASSESSLY_SCHEMA.STREAMLIT_STAGE'
    MAIN_FILE = '/assessly_app.py'
    QUERY_WAREHOUSE = 'COMPUTE_WH'
    TITLE = 'Assessly - AI Hiring Agent';
```

### 3. Access the App

Open Snowsight → **Projects > Streamlit > ASSESSLY_APP**

## Workflow

1. **Recruiter** creates a job with requirements
2. **AI** analyzes and generates competency mapping
3. **AI** creates a tailored assessment (10 questions)
4. **Candidates** receive access tokens and take the assessment
5. **AI** evaluates responses and provides scores + feedback
6. **AI** generates hiring recommendations with confidence levels

## Project Structure

```
assessly-ai-hiring-agent/
├── README.md
├── scripts/
│   └── setup_database.sql      # Database DDL + Stored Procedures
├── streamlit/
│   ├── assessly_app.py         # Main Streamlit application
│   └── environment.yml         # Python dependencies
└── docs/
    └── product_vision.md       # Product vision document
```

## License

MIT
