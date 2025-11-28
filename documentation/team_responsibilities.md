# Team Responsibilities

## 1. Business Analysts (BA) - 5-6 people
**What You Own:**
*   Business requirements gathering
*   KPI definitions (CAC, LTV, churn rate, AOV)
*   Intervention strategies (what to do with predictions)
*   ROI calculations
*   Stakeholder presentations

**Key Questions You Answer:**
*   What business problem are we solving?
*   How do we measure success?
*   What actions do we take based on model outputs?
*   What's the expected ROI?

**Deliverables:**
*   Business Requirements Document (BRD)
*   KPI framework
*   Intervention playbook (if churn risk > 70%, send 15% discount)
*   ROI analysis
*   Executive presentation

**You DON'T:**
*   Build dashboards (that's DA)
*   Write code (that's DE/DS)
*   Deploy anything technical

---

## 2. Project Managers (PM) - 12 people
**What You Own:**
*   Sprint planning and tracking
*   Cross-team coordination
*   Dependency management
*   Risk identification
*   Status reporting

**Split Responsibilities (3 sub-teams of 4):**
*   **Team 1:** Coordinate DE + DS (technical integration)
*   **Team 2:** Coordinate DA + BA (business alignment)
*   **Team 3:** Testing, documentation, delivery management

**Key Artifacts:**
*   Project charter
*   Sprint backlog (JIRA/Trello)
*   Weekly status reports
*   Dependency tracker
*   Risk register

**You DON'T:**
*   Make technical decisions
*   Define business requirements
*   Build anything (you coordinate builders)

---

## 3. Data Engineers (DE) - TBD
**What You Own:**
*   Data pipelines (batch processing)
*   AWS S3 data lake architecture
*   Data quality monitoring
*   dbt transformations
*   Star schema design

**Your Tasks:**
*   Extract data from AWS RDS → AWS S3 (raw layer)
*   Build S3 folder structure (raw/staging/curated)
*   Create dbt transformations (clean + business logic)
*   Build star schema in S3 or Redshift Spectrum
*   Provide clean data to DS and DA teams
*   Monitor data quality

**Deliverables:**
*   S3 data lake (3 layers)
*   dbt project (5+ transformation models)
*   Star schema (fact_orders, dim_customers, etc.)
*   Data quality dashboard
*   Architecture diagram
*   Documentation

**You DON'T:**
*   Train ML models (that's DS)
*   Build prediction APIs (that's DS)
*   Create business dashboards (that's DA)

---

## 4. Data Scientists (DS) - 6 people
**What You Own:**
*   ML models (churn, recommendation, CLV)
*   Feature engineering
*   Model evaluation
*   API development and deployment (FastAPI)
*   Model monitoring
*   ML results dashboard (Streamlit)

**Split Work (3 teams of 2):**
*   **Team 1:** Churn model + API endpoint
*   **Team 2:** Recommendation engine + API endpoint
*   **Team 3:** CLV model + Streamlit dashboard

**Deliverables:**
*   3 trained models (>70% accuracy for churn)
*   FastAPI with 3 endpoints (/predict/churn, /recommend, /clv)
*   Model evaluation report
*   Feature importance analysis
*   Streamlit dashboard (model performance + predictions)
*   API documentation
*   Deployment guide

**You DON'T:**
*   Build data pipelines (that's DE)
*   Create business intelligence dashboards (that's DA)

---

## 5. Data Analysts (DA) - 10 people
**What You Own:**
*   Business intelligence dashboards
*   Customer segmentation
*   Exploratory analysis
*   Cohort analysis
*   Funnel analysis
*   Weekly insights

**Split Work (2-3 teams):**
*   **Team 1 (4 people):** Executive dashboard (revenue, churn trends, KPIs)
*   **Team 2 (3 people):** Customer analytics (segmentation, cohorts, personas)
*   **Team 3 (3 people):** Marketing analytics (funnel, campaign performance)

**Deliverables:**
*   3 dashboards (executive, customer, marketing)
*   Customer segmentation analysis
*   Cohort retention charts
*   Funnel analysis report
*   Customer personas
*   Weekly insights deck

**You DON'T:**
*   Build data pipelines (that's DE)
*   Train ML models (that's DS)
*   Build ML APIs (that's DS)
