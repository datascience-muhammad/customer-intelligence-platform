# Repository Collaboration & Git Workflow

This document outlines the engineering workflow for the Customer Intelligence Platform. It ensures multiple teams (DE, DS, DA) can collaborate without conflicts.

## 1. Visual Collaboration Flow
![Collaboration Flow](../assets/dev_colabs.png)

## 2. Branching Strategy

We use a tiered branching model to ensure stability while allowing parallel development.

| Branch Type | Pattern | Description |
| :--- | :--- | :--- |
| **Main** | `main` | Production-ready code. Deployed to production environments. Locked. |
| **Development** | `dev` | Integration testing branch. All team branches merge here. |
| **Team** | `team/<team-name>` | Shared workspace for sub-teams (e.g., `team/ds-churn`). Stable enough for team collaboration. |
| **Feature** | `feature/<task-name>` | Individual work branch. Short-lived. Created from Team branch. |

## 3. Detailed Workflow Steps

### Step 1: Start a New Task
Always start from your **Team Branch**, not main or dev.
```bash
# 1. Checkout your team branch and pull latest changes
git checkout team/de-pipelines
git pull origin team/de-pipelines

# 2. Create a feature branch
git checkout -b feature/add-s3-connector
```

### Step 2: Development & Commits
*   Work exclusively in your assigned folder (e.g., `data_engineering/team_a_pipelines/`).
*   Make small, frequent commits.
*   **Commit Message Format:** `<type>: <description>`
    *   `feat: add new customer churn model`
    *   `fix: resolve null values in etl`
    *   `docs: update api endpoint documentation`

### Step 3: Pull Request (PR)
1.  Push your feature branch: `git push origin feature/add-s3-connector`.
2.  Open a Pull Request on GitHub.
3.  **Important:** Set the **Base Branch** to your **Team Branch** (e.g., `team/de-pipelines`), NOT `main`.
4.  Assign a reviewer from your sub-team.

### Step 4: Review & Merge
*   **Reviewers:** Check for code quality, logic errors, and folder isolation.
*   **Approvals:** At least 1 approval required.
*   **Merge:** Squash and merge is recommended to keep history clean.

### Step 5: Promotion to Dev & Main
*   **Team Leads (PM/Lead):** Periodically merge `team/*` branches into `dev` for integration testing.
*   **Fridays:** If `dev` is stable, it is merged into `main` for the weekly release.

## 4. Best Practices
*   **Notebooks:** Clear outputs before committing `.ipynb` files to reduce bloat.
*   **Large Files:** Do not commit CSVs or models larger than 100MB. Use S3 or `.gitignore`.
*   **Conflicts:** If you encounter merge conflicts, rebase your feature branch on the team branch locally first.

```bash
git checkout feature/my-feature
git pull --rebase origin team/my-team
# Resolve conflicts
git push --force-with-lease
```
