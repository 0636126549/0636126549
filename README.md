## Job Application Autopilot

This repository includes a Python script that:

1. Reads a spreadsheet of target companies
2. Generates personalized CV PDFs
3. Generates personalized cover letter PDFs
4. Sends emails with both attachments
5. Logs status and errors to an Excel log file

## Install

```bash
pip install pandas yagmail fpdf openpyxl
```

## Required input files

- `companies.xlsx` (or CSV) with columns:
  - `Company`
  - `Email`
  - `JobTitle`
  - `CustomMessage` (optional)
- `MasterCV.txt`
- `CoverLetterTemplate.txt` using placeholders like `{Company}` and `{JobTitle}`

## Run (dry run)

```bash
python job_application_autopilot.py \
  --email-address your_email@gmail.com \
  --email-password your_app_password \
  --dry-run
```

## Run (send emails)

```bash
python job_application_autopilot.py \
  --email-address your_email@gmail.com \
  --email-password your_app_password \
  --sender-name "Your Name"
```

## Output

- PDFs are written to `generated_docs/`
- Spreadsheet log is written to `email_log.xlsx`

`Status` and `Error` columns are automatically written to the log.
